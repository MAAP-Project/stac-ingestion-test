# STAC Ingestion Test

This is a POC for a STAC Ingestion workflow that runs in GitHub actions with parallel compute power provided by [`coiled`](https://www.coiled.io/).
The goal is to create the simplest possible process for creating and ingesting STAC metadata for user-generated collections/assets.

The [`ingest` workflow](./.github/workflows/ingest.yml) authenticates with AWS and runs [`run.py`](./run.py) which reads a VEDA Dataset JSON document that specifies some details about the desired STAC collection and a few parameters that are used to find assets in S3. It uses [`rio-stac`](https://github.com/developmentseed/rio-stac) to create a STAC item.

This is just a rough example of how we could use the VEDA Dataset JSON input to generate and ingest STAC metadata for any collection.
There are definitely discovery and asset structure features that are missing in the POC but we could add that later.

It is not set up yet, but if the workflow were parameterized with `pgstac` database connection credentials, it would be able to post the resulting collections and items directly to the database.

## Details

Right now the GitHub Actions workflow will run the ingest pipeline for an Icesat2-Boreal AGB dataset consists of ~10k files in S3.
The entire process for generating the STAC metadata (which involves opening a connection to each COG in S3!) takes about 5 minutes with `coiled` cluster.
