import os, glob
import cv2
import matplotlib.pyplot as plt
import numpy as np
import math
import imageio
import multiprocessing

import micasense
import micasense.metadata as metadata
import micasense.plotutils as plotutils
import micasense.utils as msutils
import micasense.image as image
import micasense.panel as panel
import micasense.imageset as imageset
import micasense.imageutils as imageutils

DEBUG = True

def getAlignment(imageToGetAlignmentRoot, panelRoot):
    import micasense.capture as capture
    # Alignment
    imageNames = glob.glob(imageToGetAlignmentRoot)
    panelNames = glob.glob(panelRoot)

    panelCap = capture.Capture.from_filelist(panelNames) 
    imgCap = capture.Capture.from_filelist(imageNames)
    panel_reflectance_by_band = [0.67, 0.69, 0.68, 0.61, 0.67] #RedEdge band_index order
    panel_irradiance = panelCap.panel_irradiance(panel_reflectance_by_band)
    # capture.plot_undistorted_reflectance(panel_irradiance)
    imgCap.compute_reflectance(panel_irradiance)

    ## Increase max_iterations to 1000+ for better results, but much longer runtimes, but start with 100 for speed
    warp_matrices, alignment_pairs = imageutils.align_capture(imgCap, ref_index=3)#, max_iterations=10)
    
    return warp_matrices, alignment_pairs, panel_irradiance

def main(imagePath, warp_matrices, alignment_pairs, panel_irradiance):
    import micasense.capture as capture
    
    for i in range(0,201):
            imageRoot = "IMG_%04i" % i
            outputRoot = imagePath.replace('Imagery\\','').replace('\\','_') + imageRoot
            imageSet = os.path.join(imagePath,imageRoot+'_*.tif')re
            imageNames = glob.glob(imageSet)
            if not len(imageNames): continue #skip
        # try:
            imgCap = capture.Capture.from_filelist(imageNames)
            imgCap.compute_reflectance(panel_irradiance)
            
            dist_coeffs = []
            cam_mats = []
            for i,img in enumerate(imgCap.images):
                dist_coeffs.append(img.cv2_distortion_coeff())
                cam_mats.append(img.cv2_camera_matrix())

            cropped_dimensions = imageutils.find_crop_bounds(imgCap.images[0].size(), warp_matrices, dist_coeffs, cam_mats)
            im_aligned = imageutils.aligned_capture(warp_matrices, alignment_pairs, cropped_dimensions)
            im_display = np.zeros((im_aligned.shape[0],im_aligned.shape[1],5), dtype=np.float32 )

            for i in range(0,im_aligned.shape[2]):
                im_display[:,:,i] =  imageutils.normalize(im_aligned[:,:,i])

            rgb = im_display[:,:,[2,1,0]]
            cir = im_display[:,:,[3,2,1]]

            gaussian_rgb = cv2.GaussianBlur(rgb, (9,9), 10.0)
            gaussian_rgb[gaussian_rgb<0] = 0
            gaussian_rgb[gaussian_rgb>1] = 1
            unsharp_rgb = cv2.addWeighted(rgb, 1.5, gaussian_rgb, -0.5, 0)
            unsharp_rgb[unsharp_rgb<0] = 0
            unsharp_rgb[unsharp_rgb>1] = 1
            gamma = 1.4
            gamma_corr_rgb = unsharp_rgb**(1.0/gamma)

            # Output
            imtype = '.jpg' # or 'jpg'
            imageio.imwrite(os.path.join('.','Output','rgb',outputRoot+imtype), (255*gamma_corr_rgb).astype('uint8'))
            imageio.imwrite(os.path.join('.','Output','cir',outputRoot+imtype), (255*cir).astype('uint8'))

            from osgeo import gdal, gdal_array
            rows, cols, bands = im_display.shape
            driver = gdal.GetDriverByName('GTiff')
            outRaster = driver.Create(os.path.join('.','Output','5band',outputRoot+".tiff"), cols, rows, bands, gdal.GDT_Float32)

            for i in range(0,bands):
                outband = outRaster.GetRasterBand(i+1)
                outband.WriteArray(im_aligned[:,:,i])
                outband.FlushCache()

            outRaster = None
            im_aligned = None
            print ("processed " + imageSet)
        # except Exception as err:
            # print("Could not process: " + imageSet)
            # print(err)

if __name__ == '__main__':
    multiprocessing.set_start_method('spawn') 
    warp_matrices, alignment_pairs, panel_irradiance = getAlignment(r'.\Imagery\0001SET\000\IMG_0042_*.tif', r'.\Imagery\0001SET\000\IMG_0000_*.tif')
    for set in range(100):
        for sub in range(100):
            for typ in ['SET', 'DUP']:
                imageryPath = 'Imagery\\%04i%s\\%03i' % (set, typ, sub)
                if os.path.exists(imageryPath):
                    main(os.path.join('.','Imagery','0001SET','000'), warp_matrices, alignment_pairs, panel_irradiance)
