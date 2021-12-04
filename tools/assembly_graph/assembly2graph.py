"""

Convert assemblies into a graph representation

"""

import sys
import time
import argparse
from pathlib import Path
from tqdm import tqdm

from assembly_graph import AssemblyGraph


def get_input_files(input):
    """Get the input files to process"""
    input_path = Path(input)
    if not input_path.exists():
        sys.exit("Input folder/file does not exist")
    if input_path.is_dir():
        assembly_files = [f for f in input_path.glob("**/assembly.json")]
        if len(assembly_files) == 0:
            sys.exit("Input folder/file does not contain assembly.json files")
        return assembly_files
    elif input_path.name == "assembly.json":
        return [input_path]
    else:
        sys.exit("Input folder/file invalid")


def assembly2graph(args):
    """Convert assemblies to graph format"""
    input_files = get_input_files(args.input)
    if args.limit is not None:
        input_files = input_files[:args.limit]
    output_dir = Path(args.output)
    if not output_dir.exists():
        output_dir.mkdir(parents=True)
    tqdm.write(f"Converting {len(input_files)} assemblies...")
    start_time = time.time()
    for input_file in tqdm(input_files):
        ag = AssemblyGraph(input_file)
        json_file = output_dir / f"{input_file.parent.stem}_graph.json"
        ag.export_graph_json(json_file)
    print(f"Time taken: {time.time() - start_time}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input", type=str, required=True, help="Input folder/file with assembly data."
    )
    parser.add_argument(
        "--output", type=str, default="data", help="Output folder to save graphs."
    )
    parser.add_argument(
        "--limit", type=int, help="Limit the number assembly files to convert."
    )
    args = parser.parse_args()
    assembly2graph(args)
