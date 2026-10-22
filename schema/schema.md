# Phenotype database schema

The phenotype database schema is a set of 11 linked tables for phenotype data from plant experiments. Alongside the scores themselves, it records what is needed to interpret them: the plant material, the experiment and its units, what was done to them, the climate they grew in, and any extra annotations.

This document describes every table and column, the conventions that apply throughout, and the few places where the schema does not behave like an ordinary relational database.

This is **version 1.0.0** of the schema. [schema.yaml](schema.yaml) is a machine-readable copy, which the validator checks data against. The tables in this document that list the tables and their columns are written from it.

> [!NOTE]
> **In short:** the tables are linked by IDs, and every measured value is a row of its own. Scores are plain numbers, and description tables say what they mean. Two things need special handling: an empty UNID in Climate means *all units*, and Features cells hold lists like `FTID1=value1;FTID2=value2`.

## Contents

- [Overview](#overview)
  - [The tables at a glance](#the-tables-at-a-glance)
  - [How the tables fit together](#how-the-tables-fit-together)
  - [Key distinctions](#key-distinctions)
- [General conventions](#general-conventions)
  - [Names](#names) · [Identifiers](#identifiers) · [Required and optional columns](#required-and-optional-columns) · [Missing values](#missing-values) · [Data types](#data-types) · [Dates](#dates) · [Numbers and scores](#numbers-and-scores) · [GPS coordinates](#gps-coordinates) · [Free text](#free-text)
- [Special rules](#special-rules)
  - [Climate rows without a unit apply to all units](#climate-rows-without-a-unit-apply-to-all-units)
  - [Features cells hold several values](#features-cells-hold-several-values)
  - [Feature types and vocabularies](#feature-types-and-vocabularies)
  - [One intervention level per unit](#one-intervention-level-per-unit)
- [Table reference](#table-reference)
  - Plant material: [Germplasm](#germplasm) · [SeedLot](#seedlot)
  - Experiment design: [Experiment](#experiment) · [ExperimentalUnit](#experimentalunit) · [ExperimentIntervention](#experimentintervention) · [Management](#management)
  - Observations: [PhenotypeDescription](#phenotypedescription) · [Phenotype](#phenotype) · [ClimateDescription](#climatedescription) · [Climate](#climate)
  - Annotations: [Features](#features)
- [Worked example](#worked-example)
- [Rules checklist](#rules-checklist)
- [Glossary](#glossary)

## Overview

### The tables at a glance

<!-- BEGIN tables: written from schema.yaml by schema/schema_md.py, do not edit by hand -->
| Table | ID column | One row is | Filled in | Needed |
|---|---|---|---|---|
| [Germplasm](#germplasm) | GPID | a variety, line or other genetically distinct plant material | before | always |
| [SeedLot](#seedlot) | SLID | a batch of seed of one germplasm | before | always |
| [Experiment](#experiment) | EXPID | a trial or experiment | before | always |
| [ExperimentalUnit](#experimentalunit) | UNID | a unit in an experiment: a field plot, a pot, a sample, … | before | always |
| [ExperimentIntervention](#experimentintervention) | IID | the intervention level of one unit | before | in experiments with interventions |
| [Management](#management) | MMID | a treatment given to a whole experiment | during or after | if recorded |
| [PhenotypeDescription](#phenotypedescription) | PDID | a trait: what is measured, in which unit and how | before | always |
| [Phenotype](#phenotype) | PHID | one score of one trait on one unit | during or after | always |
| [ClimateDescription](#climatedescription) | CDID | a climate variable: what is measured, in which unit and how | before | with Climate |
| [Climate](#climate) | CLID | one climate measurement | during or after | if recorded |
| [Features](#features) | FTID | a kind of extra annotation | before, during or after | if needed |
<!-- END tables -->

"Filled in" is relative to the experiment. The tables also fall into a few overlapping groups:

- **Shared reference tables:** Germplasm, SeedLot, PhenotypeDescription, ClimateDescription and Features describe things that recur across experiments and datasets. They work best when the same thing has the same ID everywhere.
- **Experiment tables:** Experiment, ExperimentalUnit and ExperimentIntervention describe the set-up, and are filled in before the experiment starts.
- **Observation tables:** Phenotype and Climate hold the measured values, and are filled in during or after the experiment.
- **Field-trial tables:** Management, Climate and ClimateDescription are mostly used for field trials.

### How the tables fit together

![Relationships between the tables](https://fababase.github.io/phenotype-database-format/diagram/diagram.png)

In the [interactive diagram](https://fababase.github.io/phenotype-database-format/diagram/), the tables can be dragged around, and clicking a table highlights its links.

**Plant material.** A [Germplasm](#germplasm) row describes a variety, line or other genetically distinct material. A [SeedLot](#seedlot) is a physical batch of seed of one germplasm, harvested at a given time and place. A seed lot can point to the seed lot it was grown from, so seed can be traced back through generations.

**Experiments.** An [Experiment](#experiment) is one trial, with its location, dates and set-up. It is made up of [experimental units](#experimentalunit): the plots, pots or samples that are scored. Each unit belongs to one experiment and holds plants from one seed lot. In experiments with interventions, [ExperimentIntervention](#experimentintervention) gives the level each unit received. [Management](#management) records treatments given to the experiment as a whole.

**Observations.** Measured values are stored in long format, one per row. Each row in [Phenotype](#phenotype) is one score on one unit, and points to a [PhenotypeDescription](#phenotypedescription) that says what the number means. Each row in [Climate](#climate) is one measurement for an experiment, or for one unit in it, and points to a [ClimateDescription](#climatedescription).

**Annotations.** [Features](#features) defines extra annotations that can be attached to units and to phenotype scores when no column covers them.

### Key distinctions

**Germplasm and seed lots.** Germplasm is the genetic material; a seed lot is a physical batch of it. Units point to seed lots rather than directly to germplasm, so plants of the same variety from different harvests can be told apart. The germplasm of a unit is found through its seed lot.

**Scores and descriptions.** The Score columns in Phenotype and Climate hold only numbers. A score means nothing on its own: its description (PDID or CDID) says what was measured, in which unit and how. Categorical observations are stored as number codes, and DescriptionOfMethod gives the meaning of each code.

**Interventions and management.** An intervention is something that differs between units on purpose, such as watered or not watered, inoculated or not, or intercropped with different crops: broadly, anything you would test in an analysis of variance. It is recorded per unit, in ExperimentIntervention. Management is what the whole experiment received, such as fertiliser or herbicide, and is recorded per experiment, in Management.

**Columns and features.** Most information has its own column. Features are for information about a unit or a single score that has no column, such as the tissue a sample came from, the gene a score belongs to, or the NIR wavelength of a reading. They are for information that varies between units or scores; what is the same for all of them goes in the experiment's Description. Each feature is defined once in the Features table, and then used in the Features column of ExperimentalUnit or Phenotype.

## General conventions

### Names

Table and column names are written exactly as in this document. The [table reference](#table-reference) lists the columns of each table in their standard order.

### Identifiers

Every table has an ID column, which is its first column, and every row must have an ID. A column that refers to another table holds that table's ID.

**Rules.** The validator checks these:

- IDs hold only the letters `a`–`z` and `A`–`Z`, the digits `0`–`9` and `_`. No spaces, no `-`, and no other letters, such as `á`, `ñ` or `ø`.
- IDs are unique within their table, ignoring case: `hedin_2` and `Hedin_2` count as the same ID.
- An ID in a column that refers to another table must exist in that table, written exactly the same way, character for character.

These rules keep IDs safe wherever the data goes: `;` and `=` have occasional meanings inside some cells, `,` separates the values in CSV files, `-`, spaces and other symbols might break column names in R and many other tools, and some databases do not tell upper and lower case apart.

**Recommendations:**

- Start IDs with a letter. This may become a rule.
- Write IDs in snake_case: lower-case words joined by `_`, such as `plant_height_cm`.
- Pad numbers with zeros, so that IDs sort in order: `plot007`, not `plot7`.
- In the shared reference tables (Germplasm, SeedLot, PhenotypeDescription, ClimateDescription and Features), use the same ID for the same thing in every dataset. This matters most for GPID, which links phenotypes to other data about the same plant material, such as genomic data.
- In the tables that belong to one experiment (Experiment, ExperimentalUnit, ExperimentIntervention, Management, Phenotype and Climate), IDs should never repeat across datasets, or the datasets cannot be merged. Give each experiment an EXPID that no one else would choose, and start the other IDs of the experiment with it.
- Within an experiment, do not build IDs from information that is in other columns, such as the germplasm, treatment or date. Use the label a unit already has, or a counter. If an ID and a column disagree, the column is what counts.

#### Naming IDs

Suggested forms for each ID. Leave out the parts that do not apply.

| ID | Form | Examples |
|---|---|---|
| GPID | The name or accession the material is known by elsewhere, with other characters replaced by `_`. The original goes in Name. | `hedin_2` (Name: `Hedin/2`), `ilb_938_2` (Name: `ILB 938/2`) |
| SLID | Germplasm, then place and year of harvest | `hedin_2_flakkebjerg_2028` |
| PDID | Trait, method and scale; see [PhenotypeDescription](#phenotypedescription) | `plt_ht_mean5_cm`, `plant_height_mean_of_5_plants_cm` |
| CDID | Variable, method and unit | `air_temp_day_mean_c`, `air_temperature_daily_mean_2m_c` |
| FTID | What the feature is | `soil_type`, `plant_no`, `gene_id` |
| EXPID | Who ran it (group, institution or project), what it is about, where, and when (start year, or first and last year) | `n2crop_pot_drought_2029`, `au_mbg_n2crop_field_protein_flakkebjerg_2027_2029` |
| UNID | EXPID, then the label the unit already has: plot number, pot label or sample barcode | `n2crop_pot_drought_2029_pot017` |
| IID, MMID, PHID, CLID | EXPID, then a counter | `n2crop_pot_drought_2029_000123` |

The who and when of an EXPID are what keep it from clashing with other experiments. The what and where are for the people reading it.

### Required and optional columns

Required columns must have a value in every row. All other columns are optional and can be left empty. The [table reference](#table-reference) marks which columns are required.

### Missing values

An empty cell means that there is no value, and so do the texts `NULL`, `NA`, `N/A`, `None` and `Not applicable`, in upper or lower case. In a required column, these count as missing.

Leaving the cell empty is the recommended way to write a missing value. The texts are accepted because many programs write them.

> [!IMPORTANT]
> There is one exception: a missing UNID in [Climate](#climate) means that the row applies to **all** units in the experiment, not to none. See [Climate rows without a unit apply to all units](#climate-rows-without-a-unit-apply-to-all-units).

### Data types

| Type | Meaning | How it is written |
|---|---|---|
| ID | Identifier of a row | Letters, digits and `_`; see [Identifiers](#identifiers) |
| Text | Short text | Any text |
| Long text | Free text of any length | Any text |
| Integer | Whole number | Digits, without a decimal mark |
| Number | Any real number | `.` as the decimal mark, no thousands separators |
| Date | Calendar date | `YYYY-MM-DD` |
| Coordinates | GPS position | `latitude;longitude` |
| Feature list | One or more feature values | `FTID1=value1;FTID2=value2`; see [Features cells](#features-cells-hold-several-values) |

### Dates

Dates are written `YYYY-MM-DD` (ISO 8601): a four-digit year, a two-digit month and a two-digit day. This applies to StartDate and EndDate in Experiment, HarvestDate in SeedLot, and Date in Management, Phenotype and Climate.

### Numbers and scores

- Numbers use `.` as the decimal mark, never `,`, and have no thousands separators.
- The Score columns in [Phenotype](#phenotype) and [Climate](#climate) hold a number and nothing else: no units, words or symbols. The unit is given in the description table.
- Categorical values are stored as number codes (1, 2, 3, …). DescriptionOfMethod in the description table must say what each code means.
- Block, Column and Row in [ExperimentalUnit](#experimentalunit) are whole numbers, not text or IDs.

### GPS coordinates

Coordinates are written as latitude and longitude in decimal degrees[^wgs84], latitude first, separated by `;` and without spaces: `latitude;longitude`. Southern latitudes and western longitudes are negative. This applies to GPSCoordinates in Experiment and ExperimentalUnit.

**Example:** `56.170308;10.207013`

### Free text

Description, DescriptionOfMethod and Comments columns take any text. They are what makes the numbers usable by others, so they are worth writing with care. The validator can only check that a required one is filled in.

**Recommendations:**

- Write for someone who was not there, years later, with only these tables. If they would have to ask you to use the data, something is missing.
- Say each fact once, in its own column.
- Define every name you introduce, such as intervention levels, score codes, instruments and abbreviations.
- Give numbers with their units.
- When something changes what a number means, make it visible in the data. Depending on the case, that could be a PDID or CDID of its own, or a [feature](#features-cells-hold-several-values) such as the tissue or the days after sowing.
- Leave a cell empty rather than writing "none", "-" or "NA". An empty Comments cell is normal.
- Avoid special symbols where a word does the job: write "percent", not "%".
- Descriptions in PhenotypeDescription, ClimateDescription and Features are general, because they, ideally, will be reused across experiments.

What each of these columns should cover is in its description, in the [table reference](#table-reference).

## Special rules

A few parts of the schema do not behave like an ordinary relational database. Anyone loading the tables into a database, or checking them with a script, needs to handle these explicitly.

### Climate rows without a unit apply to all units

A row in [Climate](#climate) always belongs to an experiment (EXPID), and can also name a unit (UNID):

| UNID | The value applies to |
|---|---|
| Filled in | That unit only |
| Empty, `NULL` or another [missing value](#missing-values) | **Every unit** in the experiment |

- A UNID that is filled in must belong to the same experiment as the row's EXPID.
- This is the only column in the schema where an empty value means "all". Everywhere else, an empty value means the value is missing.

<details>
<summary>Joining Climate to units in SQL</summary>

A plain join on UNID leaves out the rows that apply to all units. Join on the experiment instead, and match the unit only when one is given:

```sql
-- Each climate value, once for every unit it applies to.
-- Assumes missing values (NULL, NA, ...) have been loaded as a real NULL.
SELECT u.UNID AS AppliesTo, c.*
FROM Climate AS c
JOIN ExperimentalUnit AS u
  ON u.EXPID = c.EXPID
 AND (c.UNID IS NULL OR c.UNID = u.UNID);
```

</details>

### Features cells hold several values

The Features columns in [ExperimentalUnit](#experimentalunit) and [Phenotype](#phenotype) can hold several feature values in one cell, written like this:

```text
FTID1=value1;FTID2=value2;…;FTIDn=valuen
```

Each entry is a feature ID from the [Features](#features) table, an `=`, and a value. Entries are separated by `;`. The cell above splits into:

| FTID | Value |
|---|---|
| FTID1 | value1 |
| FTID2 | value2 |
| … | … |
| FTIDn | valuen |

Rules:

- Every FTID must exist in the Features table, written exactly the same way.
- Each FTID appears at most once per cell.
- There are no spaces around `=` or `;`.
- Values cannot contain `;` or `=`.
- Each value must be valid for its feature's Type and Vocabulary (see [Feature types and vocabularies](#feature-types-and-vocabularies)).
- An empty cell, or a [missing value](#missing-values) such as `NULL`, means the unit or score has no features.

Features on a unit describe the whole unit: the plot, pot or sample. Features on a phenotype score describe that score only.

**Example:** TODO

> [!WARNING]
> Features cells are strict. A space after `;`, a misspelt FTID or a value outside the feature's vocabulary makes the cell invalid.

<details>
<summary>Formal syntax of a Features cell</summary>

```ebnf
features = entry , { ";" , entry } ;
entry    = ftid , "=" , value ;
ftid     = idchar , { idchar } ;   (* an FTID from the Features table *)
value    = char , { char } ;       (* valid for the feature's Type and Vocabulary *)
idchar   = ? a letter a-z or A-Z, a digit 0-9 or "_" ? ;
char     = ? any character except ";" and "=" ? ;
(* no spaces directly before or after ";" or "=" *)
```

</details>

### Feature types and vocabularies

A feature's Type sets what kind of value it takes, and its optional Vocabulary narrows down which values are allowed:

| Type | Values | Vocabulary |
|---|---|---|
| `c` | Any text | A list of allowed values separated by `;`, with no spaces around it: `value1;value2;value3` |
| `i` | Whole numbers | A range written `min..max` |
| `d` | Any real number, with `.` as the decimal mark | A range written `min..max` |

- Types are written in lower case. An empty Type is treated as `c`.
- For `c`, a value must match one of the listed values exactly. Any other value is invalid.
- For `i` and `d`, the range includes both ends (min ≤ value ≤ max), and both ends must be given.
- An empty Vocabulary allows any value of the feature's type.
- Unit gives the unit of the values, mostly for `i` and `d`.

**Example:** one feature of each type.

| FTID | Type | Unit | Vocabulary | Description |
|---|---|---|---|---|
| TODO | `c` | TODO | TODO | TODO |
| TODO | `i` | TODO | TODO | TODO |
| TODO | `d` | TODO | TODO | TODO |

<details>
<summary>Formal syntax of a Vocabulary</summary>

```ebnf
vocabulary = list | range ;
list       = term , { ";" , term } ;    (* Type c *)
range      = number , ".." , number ;   (* Type i or d; both ends included *)
term       = ? any text without ";" or "=" ? ;
number     = ? a number, with "." as the decimal mark ? ;
(* no spaces directly before or after ";" *)
```

</details>

### One intervention level per unit

In an experiment with interventions, every unit has exactly one row in [ExperimentIntervention](#experimentintervention). Control units are included, with a level of their own.

- **Intervention** holds the level the unit received. When the experiment has more than one factor, each combination of factor levels is a level of its own. A design with two water regimes and inoculation, for example, has four levels: `HighWaterInoculated`, `HighWaterNotInoculated`, `LowWaterInoculated` and `LowWaterNotInoculated`.
- **Description** describes the whole intervention system in the experiment, including all levels, so it is usually the same for every unit in the experiment. Define each level concretely: what was done, how much and when.
- Because each unit has only one row, UNID is unique in this table, just like IID.
- Experiments without interventions have no rows in this table.

## Table reference

Each table below lists its columns in standard order, as written from [schema.yaml](schema.yaml). **Required** says whether every row must have a value; *unique* means no two rows can share the same value. **Links to** names the table whose ID the column holds. Types are explained under [Data types](#data-types).

### Germplasm

Genetically distinct plant material, such as a variety or line. **One row per germplasm.**

<!-- BEGIN columns of Germplasm: written from schema.yaml by schema/schema_md.py, do not edit by hand -->
| Column | Type | Required | Links to | Description | Example |
|---|---|---|---|---|---|
| GPID | ID | Yes, unique | | Germplasm ID. | TODO |
| Name | Text | No | | Name of the variety or line. | TODO |
| AlternativeName | Text | No | | Other names for the variety. Separate several names with `;`. | TODO |
| Species | Text | No | | Species of the variety. | TODO |
| Donor | Text | No | | Donor or parent of the variety. | TODO |
| GeographicOrigin | Text | No | | Geographic origin of the variety. | TODO |
| Maintaining | Text | No | | Who maintains the variety, such as a breeder or genebank. | TODO |
| Comments | Long text | No | | What is known about the material that no column holds, such as its pedigree, breeding history or notable traits. See [Free text](#free-text). | TODO |
<!-- END columns of Germplasm -->

> [!IMPORTANT]
> GPID is what links phenotype data to other data on the same plant material, such as genomic data. Make sure it is correct, and use the same GPID for the same germplasm in every dataset.

<sub>[↑ Back to contents](#contents)</sub>

### SeedLot

A physical batch of seed of one germplasm, from one harvest. **One row per seed lot.**

<!-- BEGIN columns of SeedLot: written from schema.yaml by schema/schema_md.py, do not edit by hand -->
| Column | Type | Required | Links to | Description | Example |
|---|---|---|---|---|---|
| SLID | ID | Yes, unique | | Seed lot ID. | TODO |
| GPID | ID | Yes | [Germplasm](#germplasm) | Germplasm the seed is of. | TODO |
| HarvestDate | Date | No | | Date the seed lot was harvested. | TODO |
| HarvestLocation | Text | No | | Where the seed lot was harvested. | TODO |
| ParentSLID | ID | No | [SeedLot](#seedlot) | Seed lot this one was grown from. | TODO |
| Comments | Long text | No | | Seed quality and handling, such as germination, seed treatment or deviations from expected phenotype. See [Free text](#free-text). | TODO |
<!-- END columns of SeedLot -->

- ParentSLID points to another row in this same table, so a seed lot can be traced back through earlier generations. When it is filled in, it must be an SLID that exists in SeedLot. If the parent seed lot is not in the dataset, either add it as a row of its own or leave ParentSLID empty.
- Experimental units point to seed lots, not to germplasm. To find the germplasm of a unit, go through its seed lot.

<sub>[↑ Back to contents](#contents)</sub>

### Experiment

One trial or experiment: where and when it ran, and how it was set up. **One row per experiment.**

<!-- BEGIN columns of Experiment: written from schema.yaml by schema/schema_md.py, do not edit by hand -->
| Column | Type | Required | Links to | Description | Example |
|---|---|---|---|---|---|
| EXPID | ID | Yes, unique | | Experiment ID. | TODO |
| GPSCoordinates | Coordinates | No | | Location of the experiment. | TODO |
| PlotSize | Text | No | | Size of each plot or pot, with its unit. | TODO |
| PlotSizeIncludingPath | Text | No | | Size of each plot, including paths, with its unit. | TODO |
| StartDate | Date | No | | Start of the growing period. | TODO |
| EndDate | Date | No | | End of the growing period. | TODO |
| Description | Long text | No | | The site (address and field) or facility, growing conditions, trial size, plot layout, design and number of replicates, what the blocks are, any irrigation, which traits were tested, which factors are tested, and any other information relevant to this experiment. The levels of the factors are defined in ExperimentIntervention. See [Free text](#free-text). | TODO |
| Manager | Text | No | | Name of the person who managed the trial. | TODO |
| Distance | Text | No | | Distance to the weather station that the Climate data comes from, with its unit. | TODO |
| Comments | Long text | No | | Events that affected the whole experiment. See [Free text](#free-text). | TODO |
<!-- END columns of Experiment -->

<sub>[↑ Back to contents](#contents)</sub>

### ExperimentalUnit

A unit in an experiment that phenotypes are recorded on: a field plot, a plant pot, a sample, and so on. **One row per unit.**

<!-- BEGIN columns of ExperimentalUnit: written from schema.yaml by schema/schema_md.py, do not edit by hand -->
| Column | Type | Required | Links to | Description | Example |
|---|---|---|---|---|---|
| UNID | ID | Yes, unique | | Unit ID. | TODO |
| EXPID | ID | Yes | [Experiment](#experiment) | Experiment the unit belongs to. | TODO |
| SLID | ID | Yes | [SeedLot](#seedlot) | Seed lot the plants in the unit come from. | TODO |
| GPSCoordinates | Coordinates | No | | Location of the unit. | TODO |
| Features | Feature list | No | [Features](#features), one or more | Features of the whole unit. See [Features cells](#features-cells-hold-several-values). | TODO |
| Block | Integer | No | | Block or batch the unit belongs to. | TODO |
| Column | Integer | No | | Column the unit is in. | TODO |
| Row | Integer | No | | Row the unit is in. | TODO |
| Comments | Long text | No | | Something that happened to this unit. See [Free text](#free-text). | TODO |
<!-- END columns of ExperimentalUnit -->

- Block, Column and Row are whole numbers, not text or IDs. Explain what the blocks are in the experiment's Description.
- In experiments with interventions, the level each unit received is in [ExperimentIntervention](#experimentintervention).

<sub>[↑ Back to contents](#contents)</sub>

### ExperimentIntervention

The intervention level each unit received, in experiments where units are treated differently on purpose. **One row per unit**, in experiments with interventions only.

<!-- BEGIN columns of ExperimentIntervention: written from schema.yaml by schema/schema_md.py, do not edit by hand -->
| Column | Type | Required | Links to | Description | Example |
|---|---|---|---|---|---|
| IID | ID | Yes, unique | | Intervention ID. | TODO |
| UNID | ID | Yes, unique | [ExperimentalUnit](#experimentalunit) | Unit that received the intervention. | TODO |
| Intervention | Text | Yes | | Level the unit received. With several factors, the combination of levels, such as `HighWaterInoculated`. | TODO |
| Description | Long text | Yes | | The intervention system in the experiment, with every level defined concretely: what was done, how much and when. Also which level is the control, if there is one. See [Free text](#free-text). | TODO |
<!-- END columns of ExperimentIntervention -->

See [One intervention level per unit](#one-intervention-level-per-unit) for how designs with more than one factor are coded.

<sub>[↑ Back to contents](#contents)</sub>

### Management

Treatments given to an experiment as a whole, such as fertiliser or herbicide. **One row per treatment application.** Mostly used for field trials.

<!-- BEGIN columns of Management: written from schema.yaml by schema/schema_md.py, do not edit by hand -->
| Column | Type | Required | Links to | Description | Example |
|---|---|---|---|---|---|
| MMID | ID | Yes, unique | | Management ID. | TODO |
| EXPID | ID | Yes | [Experiment](#experiment) | Experiment that received the treatment. | TODO |
| Treatment | Text | No | | Treatment the plants got. | TODO |
| Description | Long text | No | | The product or active ingredient, how it was applied, and why. The concentration and amount go in Dosage. See [Free text](#free-text). | TODO |
| Dosage | Text | No | | Dosage of the treatment, with its unit. | TODO |
| Date | Date | No | | Date of the treatment. | TODO |
| Comments | Long text | No | | Deviations from the plan. See [Free text](#free-text). | TODO |
<!-- END columns of Management -->

- Treatments that differ between units belong in [ExperimentIntervention](#experimentintervention), not here.

<sub>[↑ Back to contents](#contents)</sub>

### PhenotypeDescription

Defines a trait: what is measured, in which unit and how. **One row per trait.**

<!-- BEGIN columns of PhenotypeDescription: written from schema.yaml by schema/schema_md.py, do not edit by hand -->
| Column | Type | Required | Links to | Description | Example |
|---|---|---|---|---|---|
| PDID | ID | Yes, unique | | Phenotype description ID. | TODO |
| PhenotypeDescription | Text | Yes | | Name of the trait. | TODO |
| Unit | Text | Yes | | Unit the trait is scored in. | TODO |
| Grouping | Text | No | | Trait class the trait belongs to, from Crop Ontology: Morphological, Phenological, Agronomical, Physiological, Abiotic stress, Biotic stress, Biochemical, Quality or Fertility. | TODO |
| DescriptionOfMethod | Long text | Yes | | What is measured, on which part of the plant, at which growth stage, with what, on how many plants and how they are chosen, how the score is calculated, and what every code means. See [Free text](#free-text). | TODO |
<!-- END columns of PhenotypeDescription -->

- The PhenotypeDescription column holds the name of the trait. The full description of the trait and its method goes in DescriptionOfMethod.
- A PDID fixes the trait, its method and its unit. This is what [Crop Ontology](https://cropontology.org) calls a variable: a trait, a method and a scale. The same trait measured in another unit or by another method needs a PDID of its own. The level a trait is scored at is part of the method, so the height of single plants, the mean height of 5 plants in a plot and a visual estimate for the whole plot are three PDIDs.
- Name a PDID after its trait, method and scale, in that order: `plant_height_mean_of_5_plants_cm`, or shorter, `plt_ht_mean5_cm`.
- Reuse the same PDID for the same trait, measured the same way, across experiments and datasets.

<sub>[↑ Back to contents](#contents)</sub>

### Phenotype

The phenotype scores. **One row per score:** one value of one trait on one unit.

<!-- BEGIN columns of Phenotype: written from schema.yaml by schema/schema_md.py, do not edit by hand -->
| Column | Type | Required | Links to | Description | Example |
|---|---|---|---|---|---|
| PHID | ID | Yes, unique | | Phenotype ID. | TODO |
| UNID | ID | Yes | [ExperimentalUnit](#experimentalunit) | Unit that was scored. | TODO |
| PDID | ID | Yes | [PhenotypeDescription](#phenotypedescription) | Trait that was scored. | TODO |
| Features | Feature list | No | [Features](#features), one or more | Features of this score. See [Features cells](#features-cells-hold-several-values). | TODO |
| Date | Date | No | | Date of scoring. | TODO |
| Score | Number | Yes | | The score. | TODO |
| ScoredBy | Text | No | | Name of the person who did the scoring. | TODO |
| Comments | Long text | No | | Something about this one value that a reader should know. See [Free text](#free-text). | TODO |
<!-- END columns of Phenotype -->

- Different traits, dates and repeated measurements on the same unit each get a row of their own.
- What Score means, and its unit, come from the PDID.

> [!IMPORTANT]
> Score holds a number and nothing else, with `.` as the decimal mark. Categorical traits are stored as number codes, explained in DescriptionOfMethod.

<sub>[↑ Back to contents](#contents)</sub>

### ClimateDescription

Defines a climate variable: what is measured, in which unit and how. **One row per climate variable.**

<!-- BEGIN columns of ClimateDescription: written from schema.yaml by schema/schema_md.py, do not edit by hand -->
| Column | Type | Required | Links to | Description | Example |
|---|---|---|---|---|---|
| CDID | ID | Yes, unique | | Climate description ID. | TODO |
| Name | Text | Yes | | Name of the climate variable. | TODO |
| Unit | Text | Yes | | Unit the variable is measured in. | TODO |
| Grouping | Text | No | | Group the variable belongs to. | TODO |
| DescriptionOfMethod | Long text | Yes | | What is measured, at which height or depth, how often it is read, how the value is calculated, and what every code means. See [Free text](#free-text). | TODO |
<!-- END columns of ClimateDescription -->

- As with traits, a CDID fixes the variable, its unit and its method. Reuse the same CDID for the same variable, measured the same way, across experiments and datasets.
- Name a CDID the same way as a PDID: `air_temperature_daily_mean_2m_c`, or shorter, `air_temp_day_mean_c`.

<sub>[↑ Back to contents](#contents)</sub>

### Climate

Climate measurements for an experiment, or for one unit in it. **One row per measurement.** Mostly used for field trials.

<!-- BEGIN columns of Climate: written from schema.yaml by schema/schema_md.py, do not edit by hand -->
| Column | Type | Required | Links to | Description | Example |
|---|---|---|---|---|---|
| CLID | ID | Yes, unique | | Climate ID. | TODO |
| EXPID | ID | Yes | [Experiment](#experiment) | Experiment the measurement belongs to. | TODO |
| UNID | ID | No | [ExperimentalUnit](#experimentalunit) | Unit the measurement belongs to. **Empty or missing means all units in the experiment.** | TODO |
| CDID | ID | Yes | [ClimateDescription](#climatedescription) | Climate variable that was measured. | TODO |
| Date | Date | No | | Date of the measurement. | TODO |
| Score | Number | Yes | | The measured value. | TODO |
| Comments | Long text | No | | Something about this one value that a reader should know. See [Free text](#free-text). | TODO |
<!-- END columns of Climate -->

> [!IMPORTANT]
> An empty UNID does not mean "no unit": the value applies to every unit in the experiment. A UNID that is filled in must belong to the experiment given by EXPID. See [Climate rows without a unit apply to all units](#climate-rows-without-a-unit-apply-to-all-units).

- Score follows the same rules as in Phenotype: a number only, with categorical values as codes explained in DescriptionOfMethod.
- If the data comes from a weather station, the distance to the station is given in the experiment's Distance column.

<sub>[↑ Back to contents](#contents)</sub>

### Features

Defines the extra annotations that can be attached to units and phenotype scores. **One row per feature.**

<!-- BEGIN columns of Features: written from schema.yaml by schema/schema_md.py, do not edit by hand -->
| Column | Type | Required | Links to | Description | Example |
|---|---|---|---|---|---|
| FTID | ID | Yes, unique | | Feature ID, used as the key in Features cells. | TODO |
| Type | Text | No | | Kind of value, in lower case: `c` for text, `i` for whole numbers, `d` for real numbers. Empty means `c`. | TODO |
| Unit | Text | No | | Unit of the values, mostly for numbers. | TODO |
| Vocabulary | Text | No | | Allowed values: a `;`-separated list for `c`, or a `min..max` range for `i` and `d`. | TODO |
| Description | Long text | Yes | | What the feature is and what its values mean. See [Free text](#free-text). | TODO |
<!-- END columns of Features -->

- Features are used in the Features columns of [ExperimentalUnit](#experimentalunit) and [Phenotype](#phenotype). See [Features cells hold several values](#features-cells-hold-several-values) and [Feature types and vocabularies](#feature-types-and-vocabularies).

<sub>[↑ Back to contents](#contents)</sub>

## Worked example

This example follows one phenotype score back through the tables to everything needed to interpret it.

**1. The score.** A row in [Phenotype](#phenotype):

| PHID | UNID | PDID | Features | Date | Score |
|---|---|---|---|---|---|
| TODO | TODO | TODO | TODO | TODO | TODO |

**2. What the score means.** Its PDID leads to [PhenotypeDescription](#phenotypedescription):

| PDID | PhenotypeDescription | Unit | DescriptionOfMethod |
|---|---|---|---|
| TODO | TODO | TODO | TODO |

**3. The annotations on the score.** Each FTID in its Features cell leads to [Features](#features):

| FTID | Type | Unit | Vocabulary | Description |
|---|---|---|---|---|
| TODO | TODO | TODO | TODO | TODO |

**4. The unit that was scored.** Its UNID leads to [ExperimentalUnit](#experimentalunit):

| UNID | EXPID | SLID | Block | Column | Row |
|---|---|---|---|---|---|
| TODO | TODO | TODO | TODO | TODO | TODO |

**5. What the unit received.** The same UNID leads to [ExperimentIntervention](#experimentintervention):

| IID | UNID | Intervention | Description |
|---|---|---|---|
| TODO | TODO | TODO | TODO |

**6. The experiment.** The unit's EXPID leads to [Experiment](#experiment):

| EXPID | GPSCoordinates | StartDate | EndDate | Description |
|---|---|---|---|---|
| TODO | TODO | TODO | TODO | TODO |

**7. The plant material.** The unit's SLID leads to [SeedLot](#seedlot), and the seed lot's GPID to [Germplasm](#germplasm):

| SLID | GPID | HarvestDate | HarvestLocation |
|---|---|---|---|
| TODO | TODO | TODO | TODO |

| GPID | Name | Species |
|---|---|---|
| TODO | TODO | TODO |

**8. The climate.** A row in [Climate](#climate) with the same EXPID and no UNID applies to this unit, along with every other unit in the experiment. Its CDID leads to [ClimateDescription](#climatedescription):

| CLID | EXPID | UNID | CDID | Date | Score |
|---|---|---|---|---|---|
| TODO | TODO | *(empty)* | TODO | TODO | TODO |

| CDID | Name | Unit | DescriptionOfMethod |
|---|---|---|---|
| TODO | TODO | TODO | TODO |

**In plain words:** TODO

## Rules checklist

A dataset follows the schema when all of the following hold.

**All tables**

- [ ] Every required column has a value in every row (`NULL`, `NA`, `N/A`, `None` and `Not applicable` count as empty).
- [ ] Every ID holds only the letters a–z and A–Z, the digits 0–9 and `_`.
- [ ] Every ID is unique within its table, ignoring case.
- [ ] Every ID that refers to another table exists in that table, written exactly the same way.

**Values**

- [ ] Dates are written `YYYY-MM-DD`.
- [ ] Score columns hold only numbers, with `.` as the decimal mark.
- [ ] Block, Column and Row are whole numbers.
- [ ] GPS coordinates are written `latitude;longitude` in decimal degrees, without spaces.
- [ ] The codes of every categorical score are explained in its DescriptionOfMethod.

**Features**

- [ ] Type is `c`, `i`, `d` or empty.
- [ ] Vocabulary is a `;`-separated list for `c`, and a `min..max` range for `i` and `d`.
- [ ] Features cells are written `FTID1=value1;FTID2=value2`, with no spaces around `=` or `;`.
- [ ] Every FTID in a Features cell exists in Features, and appears at most once in the cell.
- [ ] Every feature value fits its feature's Type and, if given, its Vocabulary.

**Specific tables**

- [ ] In SeedLot, a ParentSLID that is filled in is an SLID in SeedLot.
- [ ] Every experiment has at least one unit in ExperimentalUnit.
- [ ] In Climate, a UNID that is filled in belongs to the experiment given by EXPID.
- [ ] In experiments with interventions, every unit has exactly one row in ExperimentIntervention.

## Glossary

| Term | Meaning |
|---|---|
| Block | A group of units in an experiment, as part of the experimental design. Can also be a batch. |
| Climate variable | Something about the growing environment that is measured during an experiment. Also called a climate covariate. Defined in ClimateDescription. |
| Crop Ontology | A shared vocabulary of crop traits, at [cropontology.org](https://cropontology.org). It defines each trait by what is observed, how it is scored and on what scale. |
| Experiment | One trial, with its own location, dates and set-up. |
| Experimental unit | A unit in an experiment that is scored, such as a field plot, a pot or a sample. |
| Factor | Something varied on purpose in an experiment, such as watering. |
| Feature | An extra annotation on a unit or a phenotype score, defined in the Features table. |
| Germplasm | Genetically distinct plant material, such as a variety or line. |
| ID | The value that identifies a row. Other tables refer to the row by its ID. |
| Intervention level | The treatment a unit received: one combination of factor levels. |
| Long format | One observation per row, rather than one column per trait. |
| Management | A treatment given to a whole experiment. |
| Phenotype | An observable trait of a plant. In this schema, also a single score of a trait. |
| Score | One measured value of a trait or climate variable. |
| Seed lot | A physical batch of seed of one germplasm, from one harvest. |
| Snake case | Writing an ID as lower-case words joined by `_`, such as `plant_height_cm`. |
| Trait | Something about a plant that is measured or scored. Defined in PhenotypeDescription. |
| Vocabulary | The values a feature is allowed to take. |

[^wgs84]: WGS 84, the coordinate system used by GPS.
