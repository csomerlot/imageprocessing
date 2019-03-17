import os, exiftool

exiftoolPath=os.environ['exiftoolpath']
filename = r'C:\Users\csomerlot\Desktop\imageprocessing\Output\0000_0001SET_000_IMG_0007_radiance.tiff'

with exiftool.ExifTool(exiftoolPath) as exift:
    exif = exift.get_metadata(filename)
    
for k in exif: print(k)
print()

with exiftool.ExifTool(exiftoolPath) as exift:
    exift.execute(bytes("-GPSAltitude=78.545", 'utf-8'), bytes(filename, 'utf-8'))
    exift.execute(bytes("-GPSLatitude=43", 'utf-8'), bytes(filename, 'utf-8'))
    exift.execute(bytes("-GPSLongitude=71", 'utf-8'), bytes(filename, 'utf-8'))
    
with exiftool.ExifTool(exiftoolPath) as exift:
    exif = exift.get_metadata(filename)
    
for k in exif: print(k, exif[k])
print()
