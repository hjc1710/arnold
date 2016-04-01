import os
import shutil
import sys
import unittest

from peewee import SqliteDatabase, Model

from arnold import init, Terminator, parse_args
from arnold.models import Migration

#sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

db = SqliteDatabase('test.db')


class BasicModel(Model):
    pass


class OutOfOrderMigration(Model):
    class Meta:
        database = db


class MissingMigration(Model):
    class Meta:
        database = db


class TestMigrationFunctions(unittest.TestCase):
    def setUp(self):
        self.model = Migration
        self.model._meta.database = db
        if self.model.table_exists():
            self.model.drop_table()
        self.model.create_table()

        self.good_migration = "001_initial"
        self.bad_migration = "bad"
        self.missing_migration = "002_missing_migration"
        self.out_of_order_migration = "003_migrate_missing"
        self.missing_migration_filename = self.missing_migration + '.py'

    def tearDown(self):
        self.model.drop_table()
        BasicModel.drop_table(fail_silently=True)
        OutOfOrderMigration.drop_table(fail_silently=True)
        MissingMigration.drop_table(fail_silently=True)
        if os.path.exists('./test_config'):
            shutil.rmtree('./test_config')

        missing_migration_path = './arnold_config/migrations/{}'.format(
            self.missing_migration_filename)
        if os.path.exists(missing_migration_path):
            os.unlink(missing_migration_path)

    def test_setup_table(self):
        """Ensure that the Migration table will be setup properly"""
        # Drop the table if it exists, as we are creating it later
        if self.model.table_exists():
            self.model.drop_table()
        args = parse_args(['status'])
        Terminator(args)
        self.assertEqual(self.model.table_exists(), True)

    def do_good_migration_up(self, table_name="basicmodel"):
        """A utility to perform a successfull upwards migration"""
        args = parse_args(['up', '1'])
        termi = Terminator(args)
        termi.perform_migrations('up')
        self.assertTrue(table_name in db.get_tables())

    def do_good_migration_down(self, table_name="basicmodel"):
        """A utility to perform a successfull downwards migration"""
        args = parse_args(['down', '1'])
        termi = Terminator(args)
        termi.perform_migrations('down')
        self.assertFalse(table_name in db.get_tables())

    def test_perform_single_migration(self):
        """A simple test of _perform_single_migration"""
        self.do_good_migration_up()

    def test_perform_single_migration_already_migrated(self):
        """Run migration twice, second time should return False"""
        # technically we run it 3 times
        self.do_good_migration_up()
        self.do_good_migration_up("outofordermigration")

        args = parse_args(['up', '1'])
        termi = Terminator(args)
        self.assertFalse(termi.perform_migrations('up'))

    def test_perform_single_migration_not_found(self):
        """Ensure that a bad migration argument raises an error"""
        args = parse_args(['up', '1'])
        termi = Terminator(args)

        with self.assertRaises(ImportError):
            termi.direction = 'up'
            termi._perform_single_migration('up')

    def test_perform_single_migration_down(self):
        """A simple test of _perform_single_migration down"""
        self.do_good_migration_up()

        self.do_good_migration_down()

    def test_perform_single_migration_down_does_not_exist(self):
        """Ensure False response when migration isn't there"""
        args = parse_args(['down', '1'])
        termi = Terminator(args)

        self.assertFalse(termi.perform_migrations('down'))

    def test_perform_single_migration_adds_deletes_row(self):
        """Make sure that the migration rows are added/deleted"""
        self.do_good_migration_up()

        self.assertTrue(self._migration_row_exists(self.good_migration))

        self.do_good_migration_down()

        self.assertFalse(self._migration_row_exists(self.good_migration))

    def test_with_fake_argument_returns_true_no_table(self):
        """If we pass fake, return true, but don't create the model table"""
        args = parse_args(['up', '1', '--fake', 'true'])
        termi = Terminator(args)
        self.assertTrue(termi.perform_migrations('up'))
        self.assertFalse("basicmodel" in db.get_tables())

    def test_filenames_include_good_migration(self):
        args = parse_args(['up', '1'])
        termi = Terminator(args)
        filenames = termi._retreive_filenames()
        self.assertTrue(self.good_migration in filenames)

    def test_init_creates_folders(self):
        args = parse_args(['init', '--folder', 'test_config'])
        self.assertTrue(init(args))
        self.assertTrue(os.path.exists('./test_config'))
        self.assertTrue(os.path.exists('./test_config/migrations'))
        self.assertTrue(os.path.isfile('./test_config/__init__.py'))
        self.assertTrue(os.path.isfile('./test_config/migrations/__init__.py'))

    def test_out_of_order_migrations(self):
        """If we don't pass --migrate-missing, don't migrate out of order."""
        # set up the state where an out of order migration can happen
        args = parse_args(['up', '0'])
        termi = Terminator(args)
        termi.perform_migrations('up')

        def _assertions():
            self.assertTrue('outofordermigration' in db.get_tables())
            self.assertFalse('missingmigration' in db.get_tables())
            self.assertTrue(self._migration_row_exists(
                    self.out_of_order_migration))
            self.assertFalse(self._migration_row_exists(self.missing_migration))
        # assert that the setup succeeded
        _assertions()

        # move the migration so we're in a proper missing state
        shutil.copy('./assets/002_missing_migration.py',
                    './arnold_config/migrations/')
        termi = Terminator(args)
        termi.perform_migrations('up')

        # now that we've migrated, make sure we didn't add that table.
        _assertions()

    def test_migrate_missing(self):
        """If we pass --migrate-missing, run out of order migrations"""
        self.test_out_of_order_migrations()

        # now let's ensure we add the table.
        args = parse_args(['up', '0', '--migrate-missing'])
        termi = Terminator(args)
        termi.perform_migrations('up')

        self.assertTrue('outofordermigration' in db.get_tables())
        self.assertTrue('missingmigration' in db.get_tables())

        self.assertTrue(self._migration_row_exists(self.out_of_order_migration))
        self.assertTrue(self._migration_row_exists(self.missing_migration))

    def test_migrate_missing_prevents_down(self):
        """Prevent going down with --migrate-missing."""
        self.do_good_migration_up()
        args = parse_args(['down', '0'])
        termi = Terminator(args)
        # manually set this because the parser doesn't support it
        termi.migrate_missing = True
        self.assertFalse(termi.perform_migrations('down'))

    def test_migrate_0_migrates_all(self):
        """Up 0 should migrate everything."""
        args = parse_args(['up', '0'])
        termi = Terminator(args)
        termi.perform_migrations('up')

        self.assertTrue(self._migration_row_exists(self.good_migration))
        self.assertTrue(self._migration_row_exists(self.out_of_order_migration))

    def _migration_row_exists(self, migration_name):
        """Assert a row exists in the migrations table with this name."""
        return self.model.select().where(
                self.model.migration == migration_name
        ).limit(1).exists()


if __name__ == '__main__':
    unittest.main()
