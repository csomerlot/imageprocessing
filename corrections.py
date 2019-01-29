import os, datetime, json, glob

from osgeo import gdal, gdal_array
import cv2
import imageio

import micasense
import micasense.capture as capture
import micasense.image as image
import micasense.metadata as metadata
import micasense.utils as msutils
import micasense.panel as panel

def log(message):
    if type(message) not in [str]:
        message = json.dumps(message, sort_keys=True, indent=4, separators=(',', ': '))
    else:
        message = message.encode('utf-8').strip()
    print(message)
    with open(__file__ + ".log", 'a') as logfil:
        logfil.write("%s: %s\n" % (datetime.datetime.now(), message))
    
def sortImageryByAlt(path, cutoffElev):
    '''sort imagery into lists of panel images or flight images'''
    data = {}
    count = 0
    for i in range(100):
        for typ in ['SET', 'DUP']:
            iset = '%04i%s' % (i, typ)
            if os.path.exists(os.path.join(path, iset)):
                for j in range(100):
                    sub = '%03i' % j
                    if os.path.exists(os.path.join(path, iset, sub)):
                        images = []
                        panels = []
                        for img in range(2001):
                            fname = 'IMG_%04i_*.tif' % (img)
                            found = True
                            for band in range(1,6):
                                imageryPath = os.path.join(path, iset, sub, fname.replace("*",str(band)))
                                if os.path.exists(imageryPath):
                                    count +=1
                                else:
                                    found = False
                            print (count, imageryPath, "complete:", found)
                            if found:
                                meta = metadata.Metadata(imageryPath, exiftoolPath=os.environ['exiftoolpath'])
                                if meta.position()[2] > cutoffElev:
                                    images.append(fname)
                                else:
                                    panels.append(fname)
                        for k in [images, panels]:
                            if k:
                                if iset not in data: data[iset] = {}
                                if sub not in data[iset]: data[iset][sub] = {}
                        if images:
                            data[iset][sub]['images'] = images
                        if panels:
                            data[iset][sub]['panels'] = panels
                            
    return data

def printMeta(imageryPath):
    print("\n",i)
    meta = metadata.Metadata(imageryPath, exiftoolPath=os.environ['exiftoolpath'])
    for k in sorted(meta.get_all().keys()):
        print('{0}: {1}'.format(k, meta.get_item(k)))
        
def getPanelData(panelRoot, plot=False):
    panelNames = glob.glob(panelRoot)
    # for i in panelNames: printMeta(i)
    panelCap = capture.Capture.from_filelist(panelNames) 
    
    if plot: panelCap.plot_panels(panelRoot[:-5].replace("\\","_")+"check.jpg")
    panel_reflectance_by_band = [0.67, 0.69, 0.68, 0.61, 0.67] #RedEdge band_index order
    panel_irradiance = panelCap.panel_irradiance(panel_reflectance_by_band)
    
    return panel_irradiance
    
def processImage(iset, sub, imagePath, imageRoot, band, radianceToReflectance):
    '''Does 3 steps: converts raw image to radiance based on metadata, converts radiance to relfectance based on panel calibration, un-distorts based on lens correction'''
    outnm = 'Output\\%04i_%s_%s_%s' % (band, iset, sub, imageRoot)
    img = image.Image(imagePath)
    outImg = img.undistorted(img.reflectance(radianceToReflectance))
    rows, cols = outImg.shape
    driver = gdal.GetDriverByName('GTiff')
    outRaster = driver.Create(outnm +"_radiance.tiff", cols, rows, 1, gdal.GDT_Float32)

    outband = outRaster.GetRasterBand(1)
    outband.WriteArray(outImg[:,:])
    outband.FlushCache()
    

    
if __name__ == '__main__':
    if os.path.exists('imagestack.jsn'): # manually create this file from the json in the log file if you want to skip this processing step
        with open('imagestack.jsn') as datfile:
            data = json.load(datfile)
    else:
        data = sortImageryByAlt('Imagery', 20)
        log(data)
    
    if os.path.exists('panelIrradiances.jsn'): # manually create this file from the json in the log file if you want to skip this processing step
        with open('panelIrradiances.jsn') as datfile:
            panelIrradiances = json.load(datfile)
    else:
        panelIrradiances = {}    
        for iset in daqta:
            for sub in data[iset]:
                if 'panels' in data[iset][sub]:
                    
                    for imageroot in data[iset][sub]['panels']:
                        panelRoot = os.path.join('Imagery', iset, sub, imageroot)
                        log(panelRoot)
                        try:
                            panel_irradiance = getPanelData(panelRoot, False)
                            panel_time = int(round(os.path.getctime(panelRoot.replace("*","1"))))
                            panelIrradiances[panelRoot[:-6]] = panel_irradiance, panel_time
                        except panel.PanelDetectionError as err:
                            log(str(err))
        log(panelIrradiances)
    
    panelTimes = {}
    for p in panelIrradiances:
        # print (panelIrradiances[p], p)
        panelTimes[panelIrradiances[p][1]] = p
        
    for iset in data:
        for sub in data[iset]:
            if 'images' in data[iset][sub]:
                for imageroot in data[iset][sub]['images']:
                    imageTime = os.path.getctime(os.path.join('Imagery', iset, sub, imageroot.replace("*","1")))
                    panelTime = min(panelTimes.keys(), key=lambda x:abs(x-imageTime))
                    panelIrradiance = panelIrradiances[panelTimes[panelTime]]
                    log("Image %s matched to panel %s" % (os.path.join('Imagery', iset, sub, imageroot), panelTimes[panelTime]))
                    
                    # image_names = glob.glob(os.path.join('Imagery', iset, sub, imageroot))
                    # cap = capture.Capture.from_filelist(image_names)
                    # cap.plot_radiance();
                    
                    for band in range(5):
                        imagePath = os.path.join('Imagery', iset, sub, imageroot.replace("*",str(band+1)))
                        processImage(iset, sub, imagePath, imageroot[:-6], band, panelIrradiance[0][band])
                    