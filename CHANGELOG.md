# Changelog

What changed in each version of the format, newest first. The current version is given in [schema/schema.yaml](schema/schema.yaml), and the [diagram](https://fababase.github.io/phenotype-database-format/diagram/) can show any version.

## Version numbers

Versions have two numbers, such as 1.2. The first goes up when existing data may have to change, and the second when it does not:

- **A new major version**, such as 2.0, means that tables that passed the validator before may now fail, or that a value now means something else. Existing datasets have to be converted again to follow it.
- **A new minor version**, such as 1.1, means that tables that passed before still pass, and mean the same. It adds something optional, such as a column or a table, or loosens a rule.

Fixes to the validator, and rewording that leaves the meaning as it is, are not new versions: the diagram keeps a drawing of every version for good, and these would only add copies of the drawing before them.

## 1.0 – 2026-11-12

The first version.
