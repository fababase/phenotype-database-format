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
  - [Files](#files) · [Names](#names) · [Identifiers](#identifiers) · [Required and optional columns](#required-and-optional-columns) · [Missing values](#missing-values) · [Data types](#data-types) · [Dates](#dates) · [Numbers and scores](#numbers-and-scores) · [GPS coordinates](#gps-coordinates) · [Free text](#free-text)
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

### Files

The tables are published, and written by the validator, as files like this:

- One CSV file per table, named after the table: `Germplasm.csv`, `SeedLot.csv`, …
- UTF-8 text, with the values separated by commas.
- The first row holds the column names: every column of the table, in the order of the [table reference](#table-reference). Each row after it is one row of the table.
- No row is empty, or holds only missing values. The validator drops such rows at the end of a file or sheet, as Excel often leaves some there unseen, but one with rows after it is an error, as it may end the table, with something else below it.
- A value with a comma, a double quote or a line break in it is put in double quotes, and a double quote in it is written twice.
- A missing value is an empty cell.
- A table that is not used is left out, or is a file with only the first row.

**Example:** `Germplasm.csv` of the dataset in the [worked example](#worked-example). Ostrin has no AlternativeName or Donor, and Belkar's Comments has a comma in it.

```text
GPID,Name,AlternativeName,Species,Donor,GeographicOrigin,Maintaining,Comments
vandrel,Vandrel,NB 117,Vicia faba,Nordbean breeding programme,Denmark,Nordbean breeding programme,Small-seeded field bean line selected for early flowering. The seeds are round and buff coloured.
ostrin,Ostrin,,Vicia faba,,Egypt,Nordbean genebank,Landrace collected in the Nile delta in 1987. Large flat seeds.
belkar,Belkar,,Vicia faba,Nordbean breeding programme,Denmark,Nordbean genebank,"Line low in vicine and convicine, selected from a cross between Vandrel and Ostrin."
```

### Names

Table and column names are written exactly as in this document. The [table reference](#table-reference) lists the columns of each table in their standard order.

### Identifiers

Every table has an ID column, which is its first column, and every row must have an ID. A column that refers to another table holds that table's ID.

**Rules.** The validator checks these:

- IDs hold only the letters `a`–`z` and `A`–`Z`, the digits `0`–`9` and `_`. No spaces, no `-`, and no other letters, such as `á`, `ñ` or `ø`.
- IDs start with a letter: `plot007`, not `007` or `_007`.
- IDs are unique within their table, ignoring case: `hedin_2` and `Hedin_2` count as the same ID.
- An ID in a column that refers to another table must exist in that table, written exactly the same way, character for character.

These rules keep IDs safe wherever the data goes: `;` and `=` have occasional meanings inside some cells, `,` separates the values in CSV files, `-`, spaces, other symbols and a digit or `_` at the start might break column names in R and many other tools, and some databases do not tell upper and lower case apart.

**Recommendations:**

- Write IDs in snake_case: lower-case words joined by `_`, such as `plant_height_cm`.
- Pad numbers with zeros, so that IDs sort in order: `plot007`, not `plot7`.
- In the shared reference tables (Germplasm, SeedLot, PhenotypeDescription, ClimateDescription and Features), use the same ID for the same thing in every dataset. This matters most for GPID, which links phenotypes to other data about the same plant material, such as genomic data. The known datasets, to look up IDs in, are listed in [datasets.md](https://github.com/fababase/phenotype-database-format/blob/main/docs/datasets.md).
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
| ID | Identifier of a row | Letters, digits and `_`, starting with a letter; see [Identifiers](#identifiers) |
| Text | Short text | Letters, digits, spaces and the symbols of a US keyboard, apart from `;` and `=` |
| Long text | Free text of any length | As text, and line breaks |
| List | Several values of text | `value1;value2`, with no spaces around `;` |
| Integer | Whole number | Digits, without a decimal mark |
| Number | Any real number | `.` as the decimal mark, no thousands separators; see [Numbers and scores](#numbers-and-scores) |
| Date | Calendar date | `YYYY-MM-DD`; see [Dates](#dates) |
| Coordinates | GPS position | `latitude;longitude`; see [GPS coordinates](#gps-coordinates) |
| Feature list | One or more feature values | `FTID1=value1;FTID2=value2`; see [Features cells](#features-cells-hold-several-values) |

**Characters.** Digits are always `0`–`9`, not full-width digits such as `１` or Arabic-Indic ones such as `٣`. Text can hold letters of any language, but no other characters beyond the symbols of a US keyboard (ASCII). Symbols such as `°`, `µ`, `–` and curly quotes are garbled when a file is read in the wrong encoding, so write them in words, such as "degrees". Text cannot hold `;` or `=`, as they have meanings of their own: `;` separates the values of lists, coordinates and Features cells, and `=` joins an FTID to its value.

### Dates

Dates are written `YYYY-MM-DD` (ISO 8601): a four-digit year, a two-digit month and a two-digit day. This applies to StartDate and EndDate in Experiment, HarvestDate in SeedLot, and Date in Management, Phenotype and Climate.

Dates have to make sense together:

- No date is in the future, not even a planned EndDate: data is added once an experiment has ended.
- An experiment's StartDate is not after its EndDate. They can be the same day.
- Phenotype dates are not before their experiment's StartDate, and Management and Climate dates are not after its EndDate. The other way round is normal: harvested seed is scored after the end, and fertiliser can be given before sowing.
- A seed lot is harvested after the seed lot it was grown from (its ParentSLID), and before the units sown from it are scored.

A date before 1950 gets a warning, as it is more often a mistake, such as `0025` for `2025`, than a real date. When a date breaks one of these rules, but would fit with day and month swapped, the validator says so.

### Numbers and scores

- Numbers use `.` as the decimal mark, never `,`, and have no thousands separators.
- Numbers are written with the digits `0`–`9`, and are not so large that they are read as infinity, such as `1e999`.
- The Score columns in [Phenotype](#phenotype) and [Climate](#climate) hold a number and nothing else: no units, words or symbols. The unit is given in the description table.
- Categorical values are stored as number codes (1, 2, 3, …). DescriptionOfMethod in the description table must say what each code means.
- Block, Column and Row in [ExperimentalUnit](#experimentalunit) are whole numbers, not text or IDs.

### GPS coordinates

Coordinates are written as latitude and longitude in decimal degrees[^wgs84], latitude first, separated by `;` and without spaces: `latitude;longitude`. Southern latitudes and western longitudes are negative. Latitude goes from −90 to 90, and longitude from −180 to 180. This applies to GPSCoordinates in Experiment and ExperimentalUnit.

**Example:** `56.170308;10.207013`

### Free text

Description, DescriptionOfMethod and Comments columns take text of any length, with line breaks, and the [characters](#data-types) of any text. They are what makes the numbers usable by others, so they are worth writing with care. Beyond those characters, the validator can only check that a required one is filled in.

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

**Example:** the Features cell `soil_type=sandy loam;soil_ph=6.4` of a field plot says that its soil is a sandy loam with pH 6.4. The Features cell `wavelength=1450;tissue=young leaf` of a leaf absorbance score says that it was measured at 1450 nm, on young leaves.

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
- For `i` and `d`, the range includes both ends (min ≤ value ≤ max). An end left blank has no limit: `0..` allows 0 and anything above it, and `..100` allows 100 and anything below it.
- An empty Vocabulary allows any value of the feature's type.
- Unit gives the unit of the values, mostly for `i` and `d`.

**Example:** one feature of each type.

| FTID | Type | Unit | Vocabulary | Description |
|---|---|---|---|---|
| soil_type | `c` | | `clay;loam;sandy loam` | Texture class of the topsoil, from a soil map. |
| plant_count | `i` | plants | | Number of plants that grew to maturity. |
| wavelength | `d` | nm | `400..2500` | Wavelength of the light that an absorbance or reflectance value was measured at. |

plant_count has no Vocabulary, so it takes any whole number.

<details>
<summary>Formal syntax of a Vocabulary</summary>

```ebnf
vocabulary = list | range ;
list       = term , { ";" , term } ;    (* Type c *)
range      = [ number ] , ".." , [ number ] ;   (* Type i or d; both ends included, a blank end has no limit *)
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
| GPID | ID | Yes, unique | | Germplasm ID. | `vandrel` |
| Name | Text | No | | Name of the variety or line. | Vandrel |
| AlternativeName | List | No | | Other names for the variety. | NB 117 |
| Species | Text | No | | Species of the variety. | Vicia faba |
| Donor | Text | No | | Donor or parent of the variety. | Nordbean breeding programme |
| GeographicOrigin | Text | No | | Geographic origin of the variety. | Denmark |
| Maintaining | Text | No | | Who maintains the variety, such as a breeder or genebank. | Nordbean breeding programme |
| Comments | Long text | No | | What is known about the material that no column holds, such as its pedigree, breeding history or notable traits. See [Free text](#free-text). | Small-seeded field bean line selected for early flowering. The seeds are round and buff coloured. |
<!-- END columns of Germplasm -->

> [!IMPORTANT]
> GPID is what links phenotype data to other data on the same plant material, such as genomic data. Make sure it is correct, and use the same GPID for the same germplasm in every dataset.

<sub>[↑ Back to contents](#contents)</sub>

### SeedLot

A physical batch of seed of one germplasm, from one harvest. **One row per seed lot.**

<!-- BEGIN columns of SeedLot: written from schema.yaml by schema/schema_md.py, do not edit by hand -->
| Column | Type | Required | Links to | Description | Example |
|---|---|---|---|---|---|
| SLID | ID | Yes, unique | | Seed lot ID. | `vandrel_northfield_2024` |
| GPID | ID | Yes | [Germplasm](#germplasm) | Germplasm the seed is of. | `vandrel` |
| HarvestDate | Date | No | | Date the seed lot was harvested. | `2024-08-29` |
| HarvestLocation | Text | No | | Where the seed lot was harvested. | Northfield research farm |
| ParentSLID | ID | No | [SeedLot](#seedlot) | Seed lot this one was grown from. | `vandrel_northfield_2023` |
| Comments | Long text | No | | Seed quality and handling, such as germination, seed treatment or deviations from expected phenotype. See [Free text](#free-text). | Germination 91 percent in a test in February 2025. |
<!-- END columns of SeedLot -->

- ParentSLID points to another row in this same table, so a seed lot can be traced back through earlier generations. When it is filled in, it must be an SLID that exists in SeedLot. If the parent seed lot is not in the dataset, either add it as a row of its own or leave ParentSLID empty.
- Going back from parent to parent never leads to the seed lot started from, however many generations back: a seed lot cannot be grown from itself or its own offspring. A seed lot is also harvested after its parent; see [Dates](#dates).
- Experimental units point to seed lots, not to germplasm. To find the germplasm of a unit, go through its seed lot.

<sub>[↑ Back to contents](#contents)</sub>

### Experiment

One trial or experiment: where and when it ran, and how it was set up. **One row per experiment.**

<!-- BEGIN columns of Experiment: written from schema.yaml by schema/schema_md.py, do not edit by hand -->
| Column | Type | Required | Links to | Description | Example |
|---|---|---|---|---|---|
| EXPID | ID | Yes, unique | | Experiment ID. | `nordbean_irrigation_northfield_2025` |
| GPSCoordinates | Coordinates | No | | Location of the experiment. | `56.091250;9.552040` |
| PlotSize | Text | No | | Size of each plot or pot, with its unit. | 3 x 5 metres (rows x columns) |
| PlotSizeIncludingPath | Text | No | | Size of each plot, including paths, with its unit. | 3.2 x 6 metres (rows x columns) |
| StartDate | Date | No | | Start of the growing period. | `2025-04-08` |
| EndDate | Date | No | | End of the growing period. | `2025-08-26` |
| Description | Long text | No | | The site (address and field) or facility, growing conditions, trial size, plot layout, design and number of replicates, what the blocks are, any irrigation, which traits were tested, which factors are tested, and any other information relevant to this experiment. The levels of the factors are defined in ExperimentIntervention. See [Free text](#free-text). | |
| Manager | Text | No | | Name of the person who managed the trial. | Rhea Plicate |
| Distance | Text | No | | Distance to the weather station that the Climate data comes from, with its unit. | 1.2 km |
| Comments | Long text | No | | Events that affected the whole experiment. See [Free text](#free-text). | A hailstorm on 2025-06-14 damaged leaves and flowers across the whole field. |
<!-- END columns of Experiment -->

<sub>[↑ Back to contents](#contents)</sub>

### ExperimentalUnit

A unit in an experiment that phenotypes are recorded on: a field plot, a plant pot, a sample, and so on. **One row per unit.**

<!-- BEGIN columns of ExperimentalUnit: written from schema.yaml by schema/schema_md.py, do not edit by hand -->
| Column | Type | Required | Links to | Description | Example |
|---|---|---|---|---|---|
| UNID | ID | Yes, unique | | Unit ID. | `nordbean_irrigation_northfield_2025_plot101` |
| EXPID | ID | Yes | [Experiment](#experiment) | Experiment the unit belongs to. | `nordbean_irrigation_northfield_2025` |
| SLID | ID | Yes | [SeedLot](#seedlot) | Seed lot the plants in the unit come from. | `vandrel_northfield_2024` |
| GPSCoordinates | Coordinates | No | | Location of the unit. | `56.091200;9.552000` |
| Features | Feature list | No | [Features](#features), one or more | Features of the whole unit. See [Features cells](#features-cells-hold-several-values). | `soil_type=sandy loam;soil_ph=6.4` |
| Block | Integer | No | | Block or batch the unit belongs to. | `1` |
| Column | Integer | No | | Column the unit is in. | `1` |
| Row | Integer | No | | Row the unit is in. | `1` |
| Comments | Long text | No | | Something that happened to this unit. See [Free text](#free-text). | Poor emergence: about 22 plants per square metre, against about 40 in the other plots. |
<!-- END columns of ExperimentalUnit -->

- Block, Column and Row are whole numbers, not text or IDs. Explain what the blocks are in the experiment's Description.
- In experiments with interventions, the level each unit received is in [ExperimentIntervention](#experimentintervention).

<sub>[↑ Back to contents](#contents)</sub>

### ExperimentIntervention

The intervention level each unit received, in experiments where units are treated differently on purpose. **One row per unit**, in experiments with interventions only.

<!-- BEGIN columns of ExperimentIntervention: written from schema.yaml by schema/schema_md.py, do not edit by hand -->
| Column | Type | Required | Links to | Description | Example |
|---|---|---|---|---|---|
| IID | ID | Yes, unique | | Intervention ID. | `nordbean_irrigation_northfield_2025_001` |
| UNID | ID | Yes, unique | [ExperimentalUnit](#experimentalunit) | Unit that received the intervention. | `nordbean_irrigation_northfield_2025_plot101` |
| Intervention | Text | Yes | | Level the unit received. With several factors, the combination of levels, such as `HighWaterInoculated`. | HighWater |
| Description | Long text | Yes | | The intervention system in the experiment, with every level defined concretely: what was done, how much and when. Also which level is the control, if there is one. See [Free text](#free-text). | |
<!-- END columns of ExperimentIntervention -->

See [One intervention level per unit](#one-intervention-level-per-unit) for how designs with more than one factor are coded.

<sub>[↑ Back to contents](#contents)</sub>

### Management

Treatments given to an experiment as a whole, such as fertiliser or herbicide. **One row per treatment application.** Mostly used for field trials.

<!-- BEGIN columns of Management: written from schema.yaml by schema/schema_md.py, do not edit by hand -->
| Column | Type | Required | Links to | Description | Example |
|---|---|---|---|---|---|
| MMID | ID | Yes, unique | | Management ID. | `nordbean_irrigation_northfield_2025_001` |
| EXPID | ID | Yes | [Experiment](#experiment) | Experiment that received the treatment. | `nordbean_irrigation_northfield_2025` |
| Treatment | Text | No | | Treatment the plants got. | Fertiliser |
| Description | Long text | No | | The product or active ingredient, how it was applied, and why. The concentration and amount go in Dosage. See [Free text](#free-text). | Phosphorus and potassium fertiliser, spread over the whole field and harrowed in before sowing. No nitrogen was given, as the crop fixes its own. |
| Dosage | Text | No | | Dosage of the treatment, with its unit. | 300 kg phosphorus and 150 kg potassium per hectare |
| Date | Date | No | | Date of the treatment. | `2025-04-03` |
| Comments | Long text | No | | Deviations from the plan. See [Free text](#free-text). | The eastern half of the field was sprayed a day later, on 2025-04-11, because of wind. |
<!-- END columns of Management -->

- Treatments that differ between units belong in [ExperimentIntervention](#experimentintervention), not here.

<sub>[↑ Back to contents](#contents)</sub>

### PhenotypeDescription

Defines a trait: what is measured, in which unit and how. **One row per trait.**

<!-- BEGIN columns of PhenotypeDescription: written from schema.yaml by schema/schema_md.py, do not edit by hand -->
| Column | Type | Required | Links to | Description | Example |
|---|---|---|---|---|---|
| PDID | ID | Yes, unique | | Phenotype description ID. | `plant_height_mean_of_5_plants_cm` |
| PhenotypeDescription | Text | Yes | | Name of the trait. | Plant height |
| Unit | Text | Yes | | Unit the trait is scored in. | cm |
| Grouping | Text | No | | Trait class the trait belongs to, from Crop Ontology: Morphological, Phenological, Agronomical, Physiological, Abiotic stress, Biotic stress, Biochemical, Quality or Fertility. | Morphological |
| DescriptionOfMethod | Long text | Yes | | What is measured, on which part of the plant, at which growth stage, with what, on how many plants and how they are chosen, how the score is calculated, and what every code means. See [Free text](#free-text). | |
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
| PHID | ID | Yes, unique | | Phenotype ID. | `nordbean_irrigation_northfield_2025_000001` |
| UNID | ID | Yes | [ExperimentalUnit](#experimentalunit) | Unit that was scored. | `nordbean_irrigation_northfield_2025_plot101` |
| PDID | ID | Yes | [PhenotypeDescription](#phenotypedescription) | Trait that was scored. | `plant_height_mean_of_5_plants_cm` |
| Features | Feature list | No | [Features](#features), one or more | Features of this score. See [Features cells](#features-cells-hold-several-values). | `wavelength=1450;tissue=young leaf` |
| Date | Date | No | | Date of scoring. | `2025-06-30` |
| Score | Number | Yes | | The score. | `94` |
| ScoredBy | Text | No | | Name of the person who did the scoring. | Rhea Plicate |
| Comments | Long text | No | | Something about this one value that a reader should know. See [Free text](#free-text). | Scored three days after the other plots, as rain stopped the scoring. |
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
| CDID | ID | Yes, unique | | Climate description ID. | `air_temperature_daily_mean_2m_c` |
| Name | Text | Yes | | Name of the climate variable. | Mean air temperature at 2 m |
| Unit | Text | Yes | | Unit the variable is measured in. | degrees Celsius |
| Grouping | Text | No | | Group the variable belongs to. | Temperature |
| DescriptionOfMethod | Long text | Yes | | What is measured, at which height or depth, how often it is read, how the value is calculated, and what every code means. See [Free text](#free-text). | Air temperature measured 2 m above the ground in a ventilated radiation shield, read every 10 minutes. The value is the mean of the readings from 00:00 to 24:00 local time. |
<!-- END columns of ClimateDescription -->

- As with traits, a CDID fixes the variable, its unit and its method. Reuse the same CDID for the same variable, measured the same way, across experiments and datasets.
- Name a CDID the same way as a PDID: `air_temperature_daily_mean_2m_c`, or shorter, `air_temp_day_mean_c`.

<sub>[↑ Back to contents](#contents)</sub>

### Climate

Climate measurements for an experiment, or for one unit in it. **One row per measurement.** Mostly used for field trials.

<!-- BEGIN columns of Climate: written from schema.yaml by schema/schema_md.py, do not edit by hand -->
| Column | Type | Required | Links to | Description | Example |
|---|---|---|---|---|---|
| CLID | ID | Yes, unique | | Climate ID. | `nordbean_irrigation_northfield_2025_003` |
| EXPID | ID | Yes | [Experiment](#experiment) | Experiment the measurement belongs to. | `nordbean_irrigation_northfield_2025` |
| UNID | ID | No | [ExperimentalUnit](#experimentalunit) | Unit the measurement belongs to. **Empty or missing means all units in the experiment.** | `nordbean_irrigation_northfield_2025_plot101` |
| CDID | ID | Yes | [ClimateDescription](#climatedescription) | Climate variable that was measured. | `soil_water_content_20cm_percent` |
| Date | Date | No | | Date of the measurement. | `2025-06-10` |
| Score | Number | Yes | | The measured value. | `27.8` |
| Comments | Long text | No | | Something about this one value that a reader should know. See [Free text](#free-text). | Includes the hail that fell in the afternoon, measured as melted water. |
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
| FTID | ID | Yes, unique | | Feature ID, used as the key in Features cells. | `soil_type` |
| Type | Text | No | | Kind of value, in lower case: `c` for text, `i` for whole numbers, `d` for real numbers. Empty means `c`. | c |
| Unit | Text | No | | Unit of the values, mostly for numbers. | nm |
| Vocabulary | List | No | | Allowed values: a `;`-separated list for `c`, or a `min..max` range for `i` and `d`. Leave an end blank for no limit, as in `0..` for 0 or more. | clay;loam;sandy loam |
| Description | Long text | Yes | | What the feature is and what its values mean. See [Free text](#free-text). | Texture class of the topsoil, from a soil map. |
<!-- END columns of Features -->

- Features are used in the Features columns of [ExperimentalUnit](#experimentalunit) and [Phenotype](#phenotype). See [Features cells hold several values](#features-cells-hold-several-values) and [Feature types and vocabularies](#feature-types-and-vocabularies).

<sub>[↑ Back to contents](#contents)</sub>

## Worked example

This example follows one phenotype score back through the tables to everything needed to interpret it. It comes from the made-up dataset in [tests/valid](../tests/valid), which the validator's tests check, and which the examples in the table reference come from too.

**1. The score.** A row in [Phenotype](#phenotype):

| PHID | UNID | PDID | Date | Score | ScoredBy |
|---|---|---|---|---|---|
| nordbean_irrigation_northfield_2025_000001 | nordbean_irrigation_northfield_2025_plot101 | plant_height_mean_of_5_plants_cm | 2025-06-30 | 94 | Rhea Plicate |

**2. What the score means.** Its PDID leads to [PhenotypeDescription](#phenotypedescription):

| PDID | PhenotypeDescription | Unit | DescriptionOfMethod |
|---|---|---|---|
| plant_height_mean_of_5_plants_cm | Plant height | cm | Height of the main stem from the soil surface to the stem tip, measured with a ruler at the end of flowering, which is growth stage 69 on the BBCH scale. Five plants per plot are measured, taking every fifth plant along one of the middle rows and skipping the outer 0.5 m at each end of the plot. The score is the mean of the five plants, rounded to the nearest cm. |

**3. The unit that was scored.** Its UNID leads to [ExperimentalUnit](#experimentalunit):

| UNID | EXPID | SLID | Features | Block | Column | Row |
|---|---|---|---|---|---|---|
| nordbean_irrigation_northfield_2025_plot101 | nordbean_irrigation_northfield_2025 | vandrel_northfield_2024 | soil_type=sandy loam;soil_ph=6.4 | 1 | 1 | 1 |

**4. The annotations on the unit.** Each FTID in the unit's Features cell leads to [Features](#features):

| FTID | Type | Unit | Vocabulary | Description |
|---|---|---|---|---|
| soil_type | c | | clay;loam;sandy loam | Texture class of the topsoil, from a soil map. |
| soil_ph | d | | | pH of the topsoil from 0 to 20 cm depth, measured in a suspension of soil in water. |

**5. What the unit received.** The same UNID leads to [ExperimentIntervention](#experimentintervention):

| IID | UNID | Intervention | Description |
|---|---|---|---|
| nordbean_irrigation_northfield_2025_001 | nordbean_irrigation_northfield_2025_plot101 | HighWater | Two water regimes, each applied to whole main plots. HighWater: drip irrigation with 15 mm of water whenever the soil water content at 20 cm depth fell below 25 percent by volume, from emergence until the end of flowering. LowWater: no irrigation, rain-fed only. LowWater is the control. |

**6. The experiment.** The unit's EXPID leads to [Experiment](#experiment):

| EXPID | GPSCoordinates | StartDate | EndDate | Description |
|---|---|---|---|---|
| nordbean_irrigation_northfield_2025 | 56.091250;9.552040 | 2025-04-08 | 2025-08-26 | Field trial at the Northfield research farm, on a field of mostly sandy loam that grew spring barley the year before. Split-plot design with 2 blocks: water regime is the main-plot factor and line the subplot factor, so each block has one main plot per water regime, with both lines in it. Each block is one row of plots running across the slope of the field. Each plot has 4 rows of plants, sown at 45 seeds per square metre. The levels of the water regime are defined in ExperimentIntervention. Weather data come from the weather station of the farm, and soil water content from sensors in some of the plots. |

**7. The plant material.** The unit's SLID leads to [SeedLot](#seedlot), and the seed lot's GPID to [Germplasm](#germplasm):

| SLID | GPID | HarvestDate | HarvestLocation | ParentSLID |
|---|---|---|---|---|
| vandrel_northfield_2024 | vandrel | 2024-08-29 | Northfield research farm | vandrel_northfield_2023 |

| GPID | Name | Species |
|---|---|---|
| vandrel | Vandrel | Vicia faba |

**8. The climate.** Rows in [Climate](#climate) with the same EXPID and no UNID apply to this unit, along with every other unit in the experiment. Rows with the unit's own UNID apply to it alone. Here is one of each. Their CDIDs lead to [ClimateDescription](#climatedescription):

| CLID | EXPID | UNID | CDID | Date | Score |
|---|---|---|---|---|---|
| nordbean_irrigation_northfield_2025_001 | nordbean_irrigation_northfield_2025 | *(empty)* | air_temperature_daily_mean_2m_c | 2025-06-14 | 14.2 |
| nordbean_irrigation_northfield_2025_003 | nordbean_irrigation_northfield_2025 | nordbean_irrigation_northfield_2025_plot101 | soil_water_content_20cm_percent | 2025-06-10 | 27.8 |

| CDID | Name | Unit | DescriptionOfMethod |
|---|---|---|---|
| air_temperature_daily_mean_2m_c | Mean air temperature at 2 m | degrees Celsius | Air temperature measured 2 m above the ground in a ventilated radiation shield, read every 10 minutes. The value is the mean of the readings from 00:00 to 24:00 local time. |
| soil_water_content_20cm_percent | Soil water content at 20 cm | percent by volume | Volumetric water content of the soil at 20 cm depth, measured with a capacitance sensor buried at that depth in the middle of the plot or pot, read every hour. The value is the mean of the readings from 00:00 to 24:00 local time. |

**In plain words:** plot 101 of the 2025 irrigation trial at the Northfield research farm grew the line Vandrel, from seed harvested there in 2024, on sandy loam with pH 6.4. It was irrigated whenever its soil water content fell below 25 percent (HighWater). On 30 June 2025, the mean height of five of its plants was 94 cm. On 10 June, its soil held 27.8 percent water by volume at 20 cm depth, and on 14 June, the mean air temperature at the trial was 14.2 degrees Celsius.

## Rules checklist

A dataset follows the schema when all of the following hold.

**All tables**

- [ ] No row without values has rows after it.
- [ ] Every required column has a value in every row (`NULL`, `NA`, `N/A`, `None` and `Not applicable` count as empty).
- [ ] Every ID holds only the letters a–z and A–Z, the digits 0–9 and `_`, and starts with a letter.
- [ ] Every ID is unique within its table, ignoring case.
- [ ] Every ID that refers to another table exists in that table, written exactly the same way.
- [ ] Text holds only letters, the digits 0–9, spaces and the symbols of a US keyboard, apart from `;` and `=`, and long text line breaks too.

**Values**

- [ ] Dates are written `YYYY-MM-DD`, and none is in the future.
- [ ] Score columns hold only numbers, with `.` as the decimal mark.
- [ ] Numbers are written with the digits 0–9, and none is so large that it is read as infinity.
- [ ] Block, Column and Row are whole numbers.
- [ ] GPS coordinates are written `latitude;longitude` in decimal degrees, without spaces, with latitude from −90 to 90 and longitude from −180 to 180.
- [ ] The codes of every categorical score are explained in its DescriptionOfMethod.

**Features**

- [ ] Type is `c`, `i`, `d` or empty.
- [ ] Vocabulary is a `;`-separated list for `c`, and a `min..max` range for `i` and `d`, where an end can be left blank.
- [ ] Features cells are written `FTID1=value1;FTID2=value2`, with no spaces around `=` or `;`.
- [ ] Every FTID in a Features cell exists in Features, and appears at most once in the cell.
- [ ] Every feature value fits its feature's Type and, if given, its Vocabulary.

**Specific tables**

- [ ] In SeedLot, a ParentSLID that is filled in is an SLID in SeedLot.
- [ ] Going back by ParentSLID never leads to the seed lot started from, and a seed lot is harvested after its ParentSLID.
- [ ] Every experiment has at least one unit in ExperimentalUnit.
- [ ] An experiment's StartDate is not after its EndDate.
- [ ] Phenotype dates are not before their experiment's StartDate, and Management and Climate dates are not after its EndDate.
- [ ] A unit is scored after the seed lot it was sown from was harvested.
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
