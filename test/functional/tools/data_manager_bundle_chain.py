"""Small data manager using Galaxy's supplied parameters and output directory."""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--database", type=Path)
    args = parser.parse_args()

    output = Path(args.output)
    params = json.loads(output.read_text())
    database = Path(params["output_data"][0]["extra_files_path"]) / "db"
    database.mkdir(parents=True)
    version = (args.database / "db_mOTU_versions").read_text() if args.database else "3.1.0"
    (database / "db_mOTU_versions").write_text(version)
    row = {"value": "motus_3.1.0", "path": str(database)}
    if params["param_dict"]["shape"] == "list":
        row["dbkey"] = "motus"
        rows = [row]
    else:
        rows = row
    output.write_text(json.dumps({"data_tables": {"testbeta": rows}}))
    print(database)


if __name__ == "__main__":
    main()
