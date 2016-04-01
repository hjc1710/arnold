Configuration
-------------

Arnold accepts a number of configuration options to the commands.

* --folder - The folder to use for configration/migrations.
* --fake   - Add the row to the database without running the migration.
* --migrate-missing - Run every migration that's missing, even if it's out of order.

.. warning::

   The ``--migrate-missing`` option can lead to data corruption or loss depending
   on how you write and name your migrations. If you prefix your migrations with a
   simple numeric string, there is a possibility they may not be run in the order
   you expect. If you prefix your migrations with the current date and time, you
   are much safer. However, if you write non-destructive migrations that don't
   heavily depend on each other (or at least other, recent ones), you'll be fine.

The `__init__.py` file inside the configuration folder holds the database value. This should be a peewee database value. Here is an example `__init__.py` file: ::

  from peewee import SqliteDatabase

  database = SqliteDatabase('test.db')
