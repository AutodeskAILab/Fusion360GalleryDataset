"""

Download and extract the Fusion 360 Gallery Assembly Dataset

"""

import argparse
import sys
import itertools
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import subprocess
from pathlib import Path
from multiprocessing.pool import ThreadPool
from multiprocessing import Pool
from tqdm import tqdm
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


def download_file(input):
    """Download a file and save it locally"""
    url, output_dir, position = input
    url_file = Path(url).name
    local_file = output_dir / url_file
    if not local_file.exists():
        tqdm.write(f"Downloading {url_file} to {local_file}")
        r = requests.get(url, stream=True, verify=False)
        if r.status_code == 200:
            total_length = int(r.headers.get("content-length"))
            pbar = tqdm(total=total_length, position=position)
            with open(local_file, "wb") as f:
                for chunk in r:
                    pbar.update(len(chunk))
                    f.write(chunk)
            pbar.close()
        tqdm.write(f"Finished downloading {local_file.name}")
    else:
        tqdm.write(f"Skipping download of {local_file.name} as local file already exists")
    return local_file


def download_files(output_dir, limit, threads):
    """Download the assembly archive files"""
    assembly_urls = [
        "https://fusion-360-gallery-dataset.s3-us-west-2.amazonaws.com/assembly/a1.0.0/a1.0.0_00.7z",
        "https://fusion-360-gallery-dataset.s3-us-west-2.amazonaws.com/assembly/a1.0.0/a1.0.0_01.7z",
        "https://fusion-360-gallery-dataset.s3-us-west-2.amazonaws.com/assembly/a1.0.0/a1.0.0_02.7z",
        "https://fusion-360-gallery-dataset.s3-us-west-2.amazonaws.com/assembly/a1.0.0/a1.0.0_03.7z",
        "https://fusion-360-gallery-dataset.s3-us-west-2.amazonaws.com/assembly/a1.0.0/a1.0.0_04.7z",
        "https://fusion-360-gallery-dataset.s3-us-west-2.amazonaws.com/assembly/a1.0.0/a1.0.0_05.7z",
        "https://fusion-360-gallery-dataset.s3-us-west-2.amazonaws.com/assembly/a1.0.0/a1.0.0_06.7z",
        "https://fusion-360-gallery-dataset.s3-us-west-2.amazonaws.com/assembly/a1.0.0/a1.0.0_07.7z",
        "https://fusion-360-gallery-dataset.s3-us-west-2.amazonaws.com/assembly/a1.0.0/a1.0.0_08.7z",
        "https://fusion-360-gallery-dataset.s3-us-west-2.amazonaws.com/assembly/a1.0.0/a1.0.0_09.7z",
        "https://fusion-360-gallery-dataset.s3-us-west-2.amazonaws.com/assembly/a1.0.0/a1.0.0_10.7z",
    ]
    if limit is not None:
        assembly_urls = assembly_urls[:limit]
    
    local_files = []
    iter_data = zip(
        assembly_urls,
        itertools.repeat(output_dir),
        itertools.count(),
    )

    results = ThreadPool(threads).imap(download_file, iter_data)
    local_files = []
    for local_file in tqdm(results, total=len(assembly_urls)):
        local_files.append(local_file)

    # Serial Implementation
    # for index, url in enumerate(assembly_urls):
    #     local_file = download_file((url, output_dir, index))
    #     local_files.append(local_file)
    return local_files


def get_7z_path():
    """Get the path to the 7-zip application"""
    # Edit the below paths to point to your install of 7-Zip
    if sys.platform == "darwin":
        zip_path = Path("/Applications/7z/7zz")
        assert zip_path.exists(), f"Could not find 7-Zip executable: {zip_path}"
        zip_path = str(zip_path.resolve())
    elif sys.platform == "win32":
        zip_path = Path("C:/Program Files/7-Zip/7z.exe")
        assert zip_path.exists(), f"Could not find 7-Zip executable: {zip_path}"
        zip_path = str(zip_path.resolve())
    elif sys.platform.startswith("linux"):
        # In linux the 7z executable is in the path
        zip_path = "7z"
    return zip_path


def extract_file(zip_path, local_file, assembly_dir):
    """Extract a single archive"""
    tqdm.write(f"Extracting {local_file.name}...")
    args = [
        zip_path,
        "x",
        str(local_file.resolve()),
        "-aos"  # Skip extracting of existing files
    ]
    p = subprocess.run(args, cwd=str(assembly_dir))
    return p.returncode == 0


def extract_files(zip_path, local_files, output_dir):
    """Extract all files"""
    # Make a sub directory for the assembly files
    assembly_dir = output_dir / "assembly"
    if not assembly_dir.exists():
        assembly_dir.mkdir(parents=True)
    results = []
    for local_file in tqdm(local_files):
        result = extract_file(zip_path, local_file, assembly_dir)
        results.append(result)
    return results


def main(output_dir, limit, threads, download_only):
    if not download_only:
        # Check we have a good path first
        zip_path = get_7z_path()

    # Download all the files, skipping those that have already been downloaded
    local_files = download_files(output_dir, limit, threads)

    if not download_only:
        # Extract all the files
        results = extract_files(zip_path, local_files, output_dir)
        tqdm.write(f"Extracted {sum(results)}/{len(results)} archives")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=str, help="Output folder to save compressed files."
    )
    parser.add_argument(
        "--limit", type=int, help="Limit the number of archive files to download."
    )
    parser.add_argument(
        "--threads", type=int, default=4, help="Number of threads to use for downloading in parallel [default: 4]."
    )
    parser.add_argument("--download_only", action="store_true", help="Download without extracting files.") 
    args = parser.parse_args()

    output_dir = None
    if args.output is not None:
        # Prep the output directory
        output_dir = Path(args.output)
        if not output_dir.exists():
            output_dir.mkdir(parents=True)

    main(output_dir, args.limit, args.threads, args.download_only)
