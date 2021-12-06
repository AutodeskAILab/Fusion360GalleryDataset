# Assembly Dataset Download
The Assembly Dataset is provided as a series of 7z archives. 
Each archive contains approximately 750 assemblies as well as the training split and license information.
The size of the entire dataset is 146.53 GB and 18.8 GB when compressed.
We provide a script to download and extract the files below.

## Download
Below are the links to directly download each of the archive files. Each archive can be extracted independently if only a portion of the full dataset is required.

- [a1.0.0_00.7z](https://fusion-360-gallery-dataset.s3-us-west-2.amazonaws.com/assembly/a1.0.0/a1.0.0_00.7z) (2.3 GB)
- [a1.0.0_01.7z](https://fusion-360-gallery-dataset.s3-us-west-2.amazonaws.com/assembly/a1.0.0/a1.0.0_01.7z) (2.1 GB)
- [a1.0.0_02.7z](https://fusion-360-gallery-dataset.s3-us-west-2.amazonaws.com/assembly/a1.0.0/a1.0.0_02.7z) (2.0 GB)
- [a1.0.0_03.7z](https://fusion-360-gallery-dataset.s3-us-west-2.amazonaws.com/assembly/a1.0.0/a1.0.0_03.7z) (1.8 GB)
- [a1.0.0_04.7z](https://fusion-360-gallery-dataset.s3-us-west-2.amazonaws.com/assembly/a1.0.0/a1.0.0_04.7z) (1.1 GB)
- [a1.0.0_05.7z](https://fusion-360-gallery-dataset.s3-us-west-2.amazonaws.com/assembly/a1.0.0/a1.0.0_05.7z) (1.9 GB)
- [a1.0.0_06.7z](https://fusion-360-gallery-dataset.s3-us-west-2.amazonaws.com/assembly/a1.0.0/a1.0.0_06.7z) (1.5 GB)
- [a1.0.0_07.7z](https://fusion-360-gallery-dataset.s3-us-west-2.amazonaws.com/assembly/a1.0.0/a1.0.0_07.7z) (1.9 GB)
- [a1.0.0_08.7z](https://fusion-360-gallery-dataset.s3-us-west-2.amazonaws.com/assembly/a1.0.0/a1.0.0_08.7z) (1.4 GB)
- [a1.0.0_09.7z](https://fusion-360-gallery-dataset.s3-us-west-2.amazonaws.com/assembly/a1.0.0/a1.0.0_09.7z) (1.2 GB)
- [a1.0.0_10.7z](https://fusion-360-gallery-dataset.s3-us-west-2.amazonaws.com/assembly/a1.0.0/a1.0.0_10.7z) (1.4 GB)


## Extraction
To extract each archive requires a tool that supports the 7z compression format.

### Linux
Distributions of Ubuntu come with `p7zip` installed. However, with older versions (e.g. 16.02) extraction times can be excessively slow. If you experience extraction times of longer than 10 mins per archive, we suggest using the latest version provided on the [7-Zip](https://www.7-zip.org) website. The following commands can be used to download and install the latest version if not already available in your package manager:

```
curl https://www.7-zip.org/a/7z2106-linux-x64.tar.xz -o 7z2106-linux-x64.tar.xz
sudo apt install xz-utils
tar -xf 7z2106-linux-x64.tar.xz
```
and then extract the archives:
```
7zz x a1.0.0_00.7z 
```

### Mac OS
On recent versions of Mac OS, 7z is supported natively.

### Windows
Windows users can download and install [7-Zip](https://www.7-zip.org), which offers both a GUI and command line interface.

## Download and Extraction Script
We provide the python script [assembly_download.py](assembly_download.py) to download and extract all archive files. 

### Installation
The script calls [7-Zip](https://www.7-zip.org) directly so if you encounter problems, ensure the path is set correctly in the `get_7z_path()` function or `7z` is present in your linux path. To run the script you will need the following python libraries that can be installed using `pip`:

- `requests`
- `tqdm`


### Running
The script can be run by passing in the output directory where the files will be extracted to. 

```
python assembly_download.py --output path/to/files
```
Additionally the following optional arguments can be passed:
- `--limit`: Limit the number of archive files to download.
- `--threads`: Number of threads to use for downloading in parallel [default: 4].
- `--download_only`: Download without extracting files.

The script will not re-download and overwrite archive files that have already been downloaded.