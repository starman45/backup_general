#!/bin/bash

# Función para comprobar variables de entorno
check_env_var() {
    if [ -z "${!1}" ]; then
        echo "ERROR: Instalation error, $1 is not defined"
        exit 1
    fi
}

# Comprobar variables de entorno necesarias
required_env_vars=("DB_ENV_POSTGRES_USER" "HOME" "DB_PORT_5432_TCP_ADDR" "ODOO_DATA_DIR" "DB_ENV_POSTGRES_PASSWORD")
for var in "${required_env_vars[@]}"; do
    check_env_var "$var"
done

# Obtener la fecha actual
NOW=$(date '+%Y-%m-%d_%H%M%S')

# Función para realizar copia de seguridad de la base de datos
backup_database() {
    database="$1"
    logfile="${database}_${NOW}-backup.log"
    db_password=$DB_ENV_POSTGRES_PASSWORD

    echo "BACKUP: DATABASE = $database, TIME = $NOW" > "$logfile"

    if ! PGPASSWORD="$db_password" /usr/bin/psql -h "$DB_PORT_5432_TCP_ADDR" -U "$DB_ENV_POSTGRES_USER" -l -F'|' -A "template1" | grep "|$DB_ENV_POSTGRES_USER|" | cut -d'|' -f1 | egrep -q "^$database$"; then
        echo "ERROR: Database '$database' not found for user '$DB_ENV_POSTGRES_USER'"
        exit 2
    fi

    echo -n "Backup database: $database ... "
    PGPASSWORD="$db_password" /usr/bin/pg_dump -Fc -v -U "$DB_ENV_POSTGRES_USER" --host "$DB_PORT_5432_TCP_ADDR" -f "${database}_${NOW}.dump" "$database" >> "$logfile" 2>&1
    error=$?
    if [ $error -eq 0 ]; then
        echo "OK"
    else
        echo "ERROR: $error"
    fi
}

# Función para realizar copia de seguridad del directorio
backup_filestore() {
    database="$1"
    logfile="${database}_${NOW}-backup.log"

    if [ ! -d "$ODOO_DATA_DIR/filestore/$database" ]; then
        echo "ERROR: Filestore '$ODOO_DATA_DIR/filestore/$database' not found"
        exit 3
    fi

    echo -n "Backup filestore: $ODOO_DATA_DIR/filestore/$database ... "
    /bin/tar -C "$ODOO_DATA_DIR/filestore" -czf "$HOME/backup/${database}_filestore_${NOW}.tar.gz" "$database" >> "$logfile" 2>&1
    error=$?
    if [ $error -eq 0 ]; then
        echo "OK"
    else
        echo "ERROR: $error"
    fi
}

# Realizar copia de seguridad de la base de datos
backup_database "$1"

# Realizar copia de seguridad del directorio
backup_filestore "$1"

# Comprimir todos los archivos de respaldo en un archivo tar.gz
echo -n "Compressing backup files: ... "
/bin/tar -czf "${1}_${NOW}.tar.gz" "${1}_${NOW}.dump" "${HOME}/backup/${1}_filestore_${NOW}.tar.gz" >> "$logfile" 2>&1
error=$?
if [ $error -eq 0 ]; then
    echo "OK"
else
    echo "ERROR: $error"
fi
echo "${1}_${NOW}.tar.gz"

