from peewee import SqliteDatabase, Model, PrimaryKeyField

from .. import database as db


class MissingMigration(Model):
    """The migration model used to track migration status"""
    id = PrimaryKeyField()

    class Meta:
        database = db


def up():
    MissingMigration.create_table(fail_silently=True)


def down():
    MissingMigration.drop_table()

