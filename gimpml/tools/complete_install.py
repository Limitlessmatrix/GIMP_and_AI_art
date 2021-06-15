"""
Script will download weights and create gimp_ml_config.pkl, and print path to be added to GIMP
"""
import os
import sys
import pickle
import csv
import hashlib
import gdown


def setup_python_weights(install_location=None):
    if not install_location:
        install_location = os.path.join(os.path.expanduser("~"), "GIMP-ML")
    if not os.path.isdir(install_location):
        os.mkdir(install_location)
    python_string = "python"
    if os.name == 'nt':  # windows
        python_string += ".exe"
    python_path = os.path.join(os.path.dirname(sys.executable), python_string)
    # with open(os.path.join(install_location, 'gimp_ml_config.pkl'), 'ab') as file:
    #     pickle.dump(python_path, file)
    # print(r"\n\n*******************", python_path)

    weight_path = os.path.join(install_location, "weights")
    if not os.path.isdir(weight_path):
        os.mkdir(weight_path)

    if os.name == 'nt':  # windows
        print("\n##########\n1>> Automatic downloading of weights not supported on Windows.")
        print("2>> Please downloads weights folder from: \n"
              "https://drive.google.com/drive/folders/10IiBO4fuMiGQ-spBStnObbk9R-pGp6u8?usp=sharing")
        print("and place in: " + weight_path)
    else:  # linux
        file_path = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(file_path, 'model_info.csv')) as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=',')
            headings = next(csv_reader)
            line_count = 0
            for row in csv_reader:
                model = row[0]
                file_id = row[1]
                fileSize = float(row[2])  # in MB
                mFName = row[3]
                md5sum = row[4]
                if not os.path.isdir(os.path.join(weight_path, model)):
                    os.mkdir(os.path.join(weight_path, model))
                destination = os.path.join(os.path.join(weight_path, model), mFName)
                if os.path.isfile(destination):
                    md5_hash = hashlib.md5()
                    a_file = open(destination, "rb")
                    content = a_file.read()
                    md5_hash.update(content)
                    digest = md5_hash.hexdigest()
                if not os.path.isfile(destination) or (digest and digest != md5sum):
                    try:
                        gimp.progress_init("Downloading " + model + "(~" + str(fileSize) + "MB)...")
                    except:
                        print("\nDownloading " + model + "(~" + str(fileSize) + "MB)...")
                    url = 'https://drive.google.com/uc?id={0}'.format(file_id)
                    gdown.cached_download(url, destination, md5=md5sum)
    plugin_loc = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(plugin_loc, 'gimp_ml_config.pkl'), 'wb') as file:
        pickle.dump({"python_path": python_path, "weight_path": weight_path}, file)

    print("3>> Please add this path to Preferences-->Plug-ins : ",
          os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "plugins"))
    print("##########\n")

if __name__ == "__main__":
    setup_python_weights()