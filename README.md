Some design notes
-----------------

Versioning:
 - ORM:
   - Each model has a __version__ attribute
   - When incrementing the version, supply an upgrader function
   - Global dict of upgraders: (tablename, fromVersion, toVersion) -> function
   - Upgrader makes direct DDL calls to alter its table / data.

 - DB:
   - "migrations" table with table name, version, is_current, schema dump (text)


On webserver startup:
 - For each model:
   - Check __version__ against is_current version in DB migrations table
   - If different, complain and bail out -- need to run a migration
   - If same, generate new schema dump (via DB) and compare that to schema in is_current.
   - If different, complain and bail out -- DB was changed without corresponding migration,
      deployment is considered broken.


Running a migration:
 - Clone DB as DB_migration_temp
 - For each model:
   - Get current DB version from migrations table
   - Get current code version from __version__
   - Attempt to find an upgrader path to get there
   - Run each upgrader in turn
   - When finished, generate new schema dump and compare to dump in migrations table
   - If different, upgrade is broken. Bail out.
 - When finished:
   - Move DB to DB_old_datetime
   - Move DB_migration_temp to DB


Creating a migration:
 - Bump __version__ in ORM definition
 - Write upgrader
 - Run migration "create" tool
   - Checks current schema against expected, as above
   - Runs upgrader on current DB table
   - Creates new schema dump and writes migration table entry
 - Manually verify, manually roll back if broken.


Adding a table:
  - As for creating a migration, above
  - Upgrader does a "CREATE TABLE"
  - Non-existing table is implicitly version 0


Issues:
 - How do we handle multiple developers writing version upgrades at once?
   - Merge tree, like git? (terrifying)
   - Don't Do That
 - Upgraders need to be run in order
   - e.g. adding a foreign key to a table being created in the same migration
   - Probably impossible to solve (databases are cyclic graphs, topological sort not enough)
   - Should be possible to manually specify an ordering between specific upgraders
   - But not required all the time