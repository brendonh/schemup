# Installation #
In your terminal (vagrant), do:

```bash
cd [repo]/protected/config
cp db.json.sample db.json
cd [repo]/protected/schema
virtualenv env
. env/bin/activate
pip install -r requirements.txt
```

Next time, when you want to run schemup:

```bash
. env/bin/activate
python update.py commit
```


# General #

Schemup versions a database on a per-table basis. This means that table X can be at version 1, while table Y can be at version 2.

All versioning data is stored in a special table called `schemup_tables`. This table keeps other (versioned) tables' schema history, including what their latest schemas should look like (somewhat similar to git history).

Schemup provides 2 main features: validation (schemas synchronization checking), and migration (schemas updating).



# Version declaration #

This is basically just a map that states what version each table should be at. There are a couple of convenient helpers to build this map.

## Storm ORM

This is achieved by using a decorator, and adding a special attribute `__version__` to model class declarations.

```python
    from storm.locals import *
    from schemup.orms import storm

    # Pass this to validate/upgrade commands. It should be a global
    # shared among model files, if there are several of them
    stormSchema = storm.StormSchema()

    @stormSchema.versioned
    class User(Storm):
        __storm_table__ = "user"
        __version__ = "knn_1"
```

## JSON file

Keep the map in a json file.

**`versions.json`**

```json
    {
        "users": "nta_6",
        "message": "ntd_9"
    }
```

**`update.py`**

```python
    class DictSchema(object):
        def __init__(self, path):
            self.versions = json.load(open(path, "r"))

        def getExpectedTableVersions(self):
            return sorted(self.versions.iteritems())

    # Pass this to validate/upgrade commands
    dictSchema = DictSchema("versions.json")
```


# Validation #

Schemup helps keeping track, for each table, of the synchronization between 3 things:

- The desired schema, declared in code, or data file (actually only version, no table structure).
- The journaled schema (cached schema, recorded schema) in `schemup_tables` (both version and table structure).
- The actual DB schema (table structure only, obviously).

Full validation happens in 2 steps:

## Checking recorded schema vs. desired schema (version mismatches) ##

This is done by simply comparing the versions declared in code with the latest version recorded in `schemup_tables`. Note that there is not (yet) an actually schema comparison.

Out-of-sync tables detected by this validation indicate that the current schema in `schemup_tables` (and thus the actual schema, provided that they are in sync) need to be brought up-to-date with the desired schema (using Schemup migration feature).

## Checking recorded schema vs. actual schema (schema mismatches) ##

This is done by getting the schema information from the DB (e.g. `information_schema.tables`), and compare them against the last recorded schema in `schemup_tables`.

Mismatches detected by this validation usually means the schema was changed outside of Schemup's control, which should be avoided.

```python
    from schemup import validator
    from warp import runtime

    conn = runtime.store.get_database().raw_connect()
    dbSchema = postgres.PostgresSchema(conn)

    errors = validator.findSchemaMismatches(dbSchema)
    if errors:
        print "Schema mismatches, was the schema changed outside Schemup?"
```



# Migration #

Schemup migration feature attempts to bring the real schema (and `schemup_tables`) up-to-date with the current ORM schema, by applying a series of "upgraders".

Each upgrader is responsible for bringing a table from one version to another, using an upgrading function that will be run on the DB schema.

An upgrader also has dependencies, which are the required versions of some tables before it can be run. For example, a foreign key referencing a table can only be added after the table is created.

There are 2 types of upgraders: those created from decorated Python functions, and those loaded from YAML files. There is a command to load both types from files under a directory.

```python
    from schemup import commands

    # Load upgraders from .py & .yaml files under "migration" directory
    commands.load("migrations")
```

After getting all the necessary upgraders, the `upgrade` command can be used to carry out the migration.

```python
    from schemup import commands
    from warp import runtime
    from models import stormSchema

    conn = runtime.store.get_database().raw_connect()
    dbSchema = postgres.PostgresSchema(conn)

    commands.upgrade(dbSchema, stormSchema)
```

## Python upgrading functions ##

Note that the logic used by these functions must be immutable over time. Therefore application logic (functions, orm classes...) from other module must not be used directly, but copied for use only in the migrations; otherwise the migrations will be broken once application logic changes.

```python
    from schemup.upgraders import upgrader

    @upgrader('user', 'bgh_2', 'bgh_3')
    def user_add_email(dbSchema):
        dbSchema.execute("ALTER TABLE user ADD email VARCHAR")
        # Or running arbitrary code here

    @upgrader('order', None, 'knn_1', dependencies=[('user', 'bgh_1')])
    def order_create(dbSchema):
        dbSchema.execute("""
            CREATE TABLE order (
                id integer NOT NULL PRIMARY KEY,
                user_id integer NOT NULL,
                CONSTRAINT order_user_id FOREIGN KEY (user_id) REFERENCES user(id)
            )
        """)
```

## Upgraders loaded from YAML files ##

One file can contain multiple blocks delineated by `---`. Each block corresponds to an upgrader. If a block's `from` key is omitted, it defaults to the previous block's `to` key.

### One table per file ###

**`user.yaml`**

```yaml
    ---
    # Another upgrader

    ---
    table: user
    from: bgh_2
    to: bgh_3
    sql: |
      ALTER TABLE user ADD email VARCHAR

    ---
    # Another upgrader
```

**`order.yaml`**

```yaml
    ---
    table: order
    from: null
    to: knn_1
    depends:
     - [ user, bgh_1 ]
    sql: |
      CREATE TABLE order (
          id integer NOT NULL PRIMARY KEY,
          user_id integer NOT NULL,
          CONSTRAINT order_user_id FOREIGN KEY (user_id) REFERENCES user(id)
      )
```
### One feature per file ###

**`feature.add-rule-table.yaml`**

```yaml
    ---
    table: questionnaire_rule
    from: null
    to: nta_1
    depends:
      - [questionnaire, nta_2]
    sql: |
      CREATE TABLE questionnaire_rule (
        id SERIAL NOT NULL PRIMARY KEY,
        created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
        issue TEXT,
        requires TEXT[2][],
        recommendations INTEGER[],
        questionnaire_id INTEGER NOT NULL REFERENCES questionnaire(id) ON DELETE RESTRICT
      );

    ---
    table: questionnaire
    from: nta_3
    to: nta_4
    depends:
      - [questionnaire_rule, nta_2]
    sql: |
      ALTER TABLE questionnaire
        DROP COLUMN rules;
```

# Snapshoting #

## Whole schema ##

Use this when you have an existing database whose schema changes need to be kept track of with Schemup.

- Add version declarations.
- Add correct schema migrations. This ensures that a new instance can be created from scratch. If there is not enough time, a workaround can be used: put the schema dump in one of the migration, leaving the rest of the migrations no-op (e.g. `SELECT 1;`). For example:

```yaml
    ---
    table: users
    from: null
    to: nta_1
    sql: |
        # The whole schema here

    ---
    table: message
    from: nul
    to: nta_1
    sql: |
        SELECT 1;

    # Other tables
```

- Use the `snapshot` command.

```python
    from schemup.dbs import postgres
    from schemup import commands
    from warp.runtime import store
    conn = store.get_database().raw_connect()
    dbSchema = postgres.PostgresSchema(conn)
    commands.snapshot(dbSchema, stormSchema)
```

## Single table (aka I mistakenly changed the schema in SQL shell) ##

Use this when you mistakenly chang a table's schema outside of schemup (e.g. trying out DDL in SQL shell without rolling back the transaction). This creates a
schema mismatch

```python
    from warp.common.schema import makeSchema
    from warp.runtime import store
    schema = makeSchema(store)
    schema.setSchema("recommendation", "nta_5")
    schema.commit()
```


# Workflow #

- When adding to an existing DB, use snapshotting.
- When starting from scratch, provide upgraders with `from` equal to `None` (python) or `null` (yaml).
- Version naming convention: programmer initials and integer id. Example: `bgh_1`, `bgh_2`, `knn_3`, `nta_4`, `knn_5`.
- Migration organization: one-feature-per-file is preferred; initial schema can be in its own file.

## Upgraders ##

- When there are schema changes, bump model classes' `__version__`.
- Put upgraders under `migrations` directory. Upgraders can be yaml files, or python files containing upgrader-decorated functions.
- Test the migration manually on a dev DB.
- Remember that Postgres DDL is transactional. Therefore it is a good idea to try out migration DDL in Postgres shell, wrapped in a transaction that will be rolled back.

```sql
    START TRANSACTION;
    -- Try CREATE TABLE, ALTER TABLE... here
    ROLLBACK;
```

## Migration ##

- Back up the DB before doing migration.
- Migration steps

```python
    from schemup.dbs import postgres
    from schemup import commands
    from warp.runtime import store

    # Get current table versions, by ORM
    from models import stormSchema

    # Get schema
    conn = store.get_database().raw_connect()
    dbSchema = postgres.PostgresSchema(conn)

    # Make sure the current DB is not "dirty"
    validator.findSchemaMismatches(dbSchema)

    # Load upgraders
    commands.load("migrations")

    # Do upgrade
    commands.upgrade(schema, stormSchema)

    # Check if the schemas are in sync
    commands.validate(runtime.schema, stormSchema)
```

## Shared dev machine ##

Schemup works on a forward-only, no-branching (directed acyclic graph) basis. This creates a problem in using shared dev machines:

- Supposed the main branch is at `user:a1`, `message:b1`.
- Developer A add migration `user:a_1` to `user:a_2` on his topic branch and test it on dev.
- Developer B add migration `message:b_1` to `message:b_2` and wants to test it on dev. He checks out his branch and runs the migration. Because `user` is at `a_2`, but the code wants it to be at `a_1`, schemup tries migrating `user` from `a_2` to `a_1` and fails not knowing how.

The best solution is to ensure that the DB's schema is the same before and after you test the code with new schema. For example:

- Make a dump of the whole database before running schema migration.
- Switch back to the branch the code was on previously after testing the new code.
- Replace the current state of the database with the dump.

## Snapshot-less application of schemup to existing DB ##

This method was by proposed Duy.
The idea is to use a dump as the DB's initial state, instead of a blank DB. The process looks like:

- Start with no migrations, blank version declarations.
- New instance are provisioned by the initial dump instead of just a blank DB.
- Continue as normal.
- New migrations should be written with the non-blank initial DB's state in mind. For example if the dump already contains a table `user`, its migrations should look like:

```yaml
    ---
    table: user
    from: null
    to: lmd_1
    sql: |
        ALTER TABLE user ADD COLUMN age INTEGER DEFAULT NULL;
```

and not

```yaml
    ---
    table: user
    from: null
    to: lmd_1
    sql: |
        CREATE TABLE user (
            # ...
        )

    ---
    table: user
    from: lmd_1
    to: lmd_2
    sql: |
        ALTER TABLE user ADD COLUMN age INTEGER DEFAULT NULL;
```
