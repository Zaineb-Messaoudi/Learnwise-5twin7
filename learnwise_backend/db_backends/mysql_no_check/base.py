from django.db.backends.mysql.base import (
    DatabaseWrapper as MySQLDatabaseWrapper,
    DatabaseFeatures as MySQLDatabaseFeatures,
)


class MySQLFeaturesNoReturning(MySQLDatabaseFeatures):
    """Desactive RETURNING (non supporte par MariaDB < 10.5)."""

    can_return_id_from_insert = False
    can_return_columns_from_insert = False


class DatabaseWrapper(MySQLDatabaseWrapper):
    """MySQL backend compatible avec MariaDB 10.4 (XAMPP)."""

    features_class = MySQLFeaturesNoReturning

    def check_database_version_supported(self):
        # Desactive la verification de version pour accepter MariaDB 10.4 (XAMPP)
        pass
