import os, shutil


def makePath(path):
    if not os.path.exists(path):
        os.mkdir(path)


for root, dirs, files in os.walk('Imagery'):
    for fil in files:
        if ' (2)' in fil:
            makePath(root.replace('SET','DUP'))
            src = os.path.join(root, fil)
            dest = os.path.join(root.replace('SET','DUP'), fil.replace(' (2)',''))
            shutil.copyfile(src, dest)
            os.remove(src)
            print ("Moved {0} to {1}".format(src, dest))