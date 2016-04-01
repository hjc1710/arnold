from peewee import SqliteDatabase, Model, PrimaryKeyField

from .. import database as db


class OutOfOrderMigration(Model):
    """The migration model used to track migration status"""
    id = PrimaryKeyField()

    class Meta:
        database = db


def up():
    OutOfOrderMigration.insert().execute()


def down():
    OutOfOrderMigration.delete().execute()

