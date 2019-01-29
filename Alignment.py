
# coding: utf-8

# # Image Alignment
# 
# In most use cases, each band of a multispectral capture must be aligned with the other bands in order to create meaningful data.  In this tutorial, we show how to align the band to each other using open source OpenCV utilities.  
# 
# Image alignment allows the combination of images into true-color (RGB) and false color (such as CIR) composites, useful for scouting using single images as well as for display and management uses.  In addition to composite images, alignment allows the calculation of pixel-accurate indices such as NDVI or NDRE at the single image level which can be very useful for applications like plant counting and coverage estimations, where mosaicing artifacts may otherwise skew analysis results.  
# 
# The image alignment method described below tends to work well on images with abundant image features, or areas of significant contrast.  Cars, buildings, parking lots, and roads tend to provide the best results.  This approach may not work well on images which contain few features or very repetitive features, such as full canopy row crops or fields of repetitive small crops such lettuce or strawberries.  We will disscuss more about the advantages and disadvantages of these methods below.
# 
# ## Opening Images
# 
# As we have done in previous examples, we use the micasense.capture class to open, radiometrically correct, and visualize the 5 bands of a RedEdge capture.
# 
# First, we'll load the `autoreload` extension.  This lets us change underlying code (such as library functions) without having to reload the entire workbook and kernel. This is useful in this workbook because the cell that runs the alignment can take a long time to run, so with `autoreload` extension we can change external code for analysis and visualization without needing to re-compute the alignments each time.

# In[ ]:


# get_ipython().run_line_magic('load_ext', 'autoreload')
# get_ipython().run_line_magic('autoreload', '2')


# In[ ]:


import os, glob
import micasense.capture as capture
# get_ipython().run_line_magic('matplotlib', 'inline')

imagePath = os.path.join('.','Imagery','0001SET','000')
imageNames = glob.glob(os.path.join(imagePath,'IMG_0003_*.tif'))
panelNames = glob.glob(os.path.join(imagePath,'IMG_0000_*.tif'))

panelCap = capture.Capture.from_filelist(panelNames) 
capture = capture.Capture.from_filelist(imageNames)
panel_reflectance_by_band = [0.67, 0.69, 0.68, 0.61, 0.67] #RedEdge band_index order
panel_irradiance = panelCap.panel_irradiance(panel_reflectance_by_band)
# Plotting the reflectance images in the capture will ensure that a reflectance image has been
# calculated for all images in the capture.
capture.plot_undistorted_reflectance(panel_irradiance)


# ## Unwarp and Align
# 
# Alignment is a three step process:
# 
# 1. Images are unwarped using the built-in lens calibration
# 1. A transformation is found to align each band to a common band
# 1. The aligned images are combined and cropped, removing pixels which don't overlap in all bands.
# 
# We provide utilities to find the alignement transformations within a single capture.  Our experience shows that once a good alignmnet transformation is found, it tends to be stable over a flight and, in most cases, over many flights.  The transformation may change if the camera undergoes a shock event (such as a hard landing or drop) or if the temperature changes substantially between flights.  In these events a new transformation may need to be found.
# 
# Further, since this approach finds a 2-dimensional (affine) transformation between images, it won't work when the parallax between bands results in a 3-dimensional depth field.  This can happen if very close to the target or when targets are visible at significantly different ranges, such as a nearby tree or building against a background much farther way. In these cases it will be necessary to use photogrammetry techniques to find a 3-dimensional mapping between images.
# 
# For best alignment results it's good to select a capture which has features which visible in all bands.  Man-made objects such as cars, roads, and buildings tend to work very well, while captures of only repeating crop rows tend to work poorly.  Remember, once a good transformation has been found for flight, it can be generally be applied across all of the images.
# 
# It's also good to use an image for alignment which is taken near the same level above ground as the rest of the flights. Above approximately 35m AGL, the alignement will be consistent. However, if images taken closer to the ground are used, such as panel images, the same alignment transformation will not work for the flight data.  

# In[ ]:


import cv2
import numpy as np
import matplotlib.pyplot as plt
import multiprocessing
import micasense.imageutils as imageutils

print("Alinging images. Depending on settings this can take from a few seconds to many minutes")
# Increase max_iterations to 1000+ for better results, but much longer runtimes
warp_matrices, alignment_pairs = imageutils.align_capture(capture, max_iterations=100)

print("Finished Aligning, warp matrices:")
for i,mat in enumerate(warp_matrices):
    print("Band {}:\n{}".format(i,mat))


# ## Crop Aligned Images
# After finding image alignments we may need to remove pixels around the edges which aren't present in every image in the capture.  To do this we use the affine transforms found above and the image distortions from the image metadata.  OpenCV provides a couple of handy helpers for this task in the  `cv2.undistortPoints()` and `cv2.transform()` methods.  These methods takes a set of pixel coordinates and apply our undistortion matrix and our affine transform, respectively.  So, just as we did when registering the images, we first apply the undistortion process the coordinates of the image borders, then we apply the affine transformation to that result. The resulting pixel coordinates tell us where the image borders end up after this pair of transformations, and we can then crop the resultant image to these coordinates.

# In[ ]:


dist_coeffs = []
cam_mats = []
# create lists of the distortion coefficients and camera matricies
for i,img in enumerate(capture.images):
    dist_coeffs.append(img.cv2_distortion_coeff())
    cam_mats.append(img.cv2_camera_matrix())
# cropped_dimensions is of the form:
# (first column with overlapping pixels present in all images, 
#  first row with overlapping pixels present in all images, 
#  number of columns with overlapping pixels in all images, 
#  number of rows with overlapping pixels in all images   )
cropped_dimensions = imageutils.find_crop_bounds(capture.images[0].size(), 
                                                 warp_matrices, 
                                                 dist_coeffs, 
                                                 cam_mats)


# ## Visualize Aligned Images
# 
# Once the transformation has been found, it can be verified by composting the aligned images to check alignment. The image 'stack' containing all bands can also be exported to a multi-band TIFF file for viewing in extrernal software such as QGIS.  Useful componsites are a naturally colored RGB as well as color infrared, or CIR. 

# In[ ]:


im_aligned = imageutils.aligned_capture(warp_matrices, alignment_pairs, cropped_dimensions)
# Create a normalized stack for viewing
im_display = np.zeros((im_aligned.shape[0],im_aligned.shape[1],5), dtype=np.float32 )

for i in range(0,im_aligned.shape[2]):
    im_display[:,:,i] =  imageutils.normalize(im_aligned[:,:,i])

rgb = im_display[:,:,[2,1,0]]
cir = im_display[:,:,[3,2,1]]
fig, axes = plt.subplots(1, 2, figsize=(16,16))
plt.title("Red-Green-Blue Composite")
axes[0].imshow(rgb)
plt.title("Color Infrared (CIR) Composite")
axes[1].imshow(cir)
plt.show()


# ## Image Enhancement
# 
# There are many techniques for image enhancement, but one which is commonly used to improve the visual sharpness of imagery is the unsharp mask.  Here we apply an unsharp mask to the RGB image to improve the visualization, and then apply a gamma curve to make the darkest areas brighter.

# In[ ]:


# Create an enhanced version of the RGB render using an unsharp mask
gaussian_rgb = cv2.GaussianBlur(rgb, (9,9), 10.0)
gaussian_rgb[gaussian_rgb<0] = 0
gaussian_rgb[gaussian_rgb>1] = 1
unsharp_rgb = cv2.addWeighted(rgb, 1.5, gaussian_rgb, -0.5, 0)
unsharp_rgb[unsharp_rgb<0] = 0
unsharp_rgb[unsharp_rgb>1] = 1

# Apply a gamma correction to make the render appear closer to what our eyes would see
gamma = 1.4
gamma_corr_rgb = unsharp_rgb**(1.0/gamma)
fig = plt.figure(figsize=(18,18))
plt.imshow(gamma_corr_rgb, aspect='equal')
plt.axis('off')
plt.show()


# ## Image Export
# 
# Composite images can be exported to JPEG or PNG format using the `imageio` package.  These images may be useful for visualization or thumbnailing, and creating RGB thumbnails of a set of images can provide a convenient way to browse the imagery in a more visually appealing way that browsing the raw imagery.   

# In[ ]:


import imageio
imtype = 'jpg' # or 'jpg'
imageio.imwrite('rgb.'+imtype, (255*gamma_corr_rgb).astype('uint8'))
imageio.imwrite('cir.'+imtype, (255*cir).astype('uint8'))


# ## Stack Export
# 
# We can export the image easily stacks using the `gdal` library (http://www.glal.org). Once exported, these image stacks can be opened in software such as QGIS and raster operations such as NDVI or NDRE computation can be done in that software.  At this time the stacks don't include any geographic information.

# In[ ]:


from osgeo import gdal, gdal_array
rows, cols, bands = im_display.shape
driver = gdal.GetDriverByName('GTiff')
outRaster = driver.Create("bgren.tiff", 
                          cols, rows, bands, gdal.GDT_Float32)

for i in range(0,bands):
    outband = outRaster.GetRasterBand(i+1)
    outband.WriteArray(im_aligned[:,:,i])
    outband.FlushCache()

outRaster = None


# ### Notes on Alignment and Stack Usage
# 
# "Stacks" as described above are useful in a number of processing cases.  For example, at the time of this writing, many photogrammetry suites could import and process stack files without significantly impacting the radiometric processing which has already been accomplished.  
# 
# Running photogrammetry on stack files instead of raw image files has both advantages and drawbacks. The primary advantage has been found to be an increase in processing speed and a reduction in program memory usage. As the photogrammetric workflow generally operates on luminance images and may not use color information, stacked images may require similar resources and be processed at a similar speed as single-band images.  This is because one band of the stack can be used to generate the matching feature space while the others are ignored for matching purposes. This reduces the feature space 5-fold over matching using all images separately.
# 
# One disadvantage is that stacking images outside of the photogrammetric workflow may result in poor image matching.  The RedEdge is known to have stable lens characteristics over the course of normal operation, but variations in temperature or impacts to the camera through handling or rough landings may change the image alignment parameters.  For this reason, we recommend finding a matching transformation for each flight (each take-off and landing).  Alignment transformations from multiple images within a flight can be compared to find the best transformation to apply to the set of the flight.  While not described or supported in this generic implementation, some matching algorithms can use a "seed" value as a starting point to speed up matching.  For most cases, this seed could be the transformation found in a previous flight, or another source of a known good transformation.    

# ## NDVI Computation
# 
# For raw index computation on single images, the numpy package provides a simple way to do math and simple visualizatoin on images.  Below, we compute and visualize an image histogram and then use that to pick a colormap range for visualizing the NDVI of an image. 
# 
# ### Plant Classification
# 
# After computing the NDVI and prior to displaying it, we use a very rudimentary method for focusing on the plants and removing the soil and shadow information from our images and histograms. Below we remove non-plant pixels by setting to zero any pixels in the image where the NIR reflectance is less than 20%.  This helps to ensure that the NDVI and NDRE histograms aren't skewed substantially by soil noise.

# In[ ]:


from micasense import plotutils
import matplotlib.pyplot as plt

np.seterr(divide='ignore', invalid='ignore') # ignore divide by zero errors in the index calculation

# Compute Normalized Difference Vegetation Index (NDVI) from the NIR(3) and RED (2) bands
ndvi = (im_aligned[:,:,3] - im_aligned[:,:,2]) / (im_aligned[:,:,3] + im_aligned[:,:,2])

# remove shadowed areas (mask pixels with NIR reflectance < 20%))
ndvi[im_aligned[:,:,3] < 0.2] = 0 

# Compute and display a histogram
hist_min = np.min(ndvi[np.where(np.logical_and(ndvi > 0, ndvi < 1))])
hist_max = np.max(ndvi[np.where(np.logical_and(ndvi > 0, ndvi < 1))])
fig, axis = plt.subplots(1, 1, figsize=(10,4))
axis.hist(ndvi.ravel(), bins=512, range=(hist_min, hist_max))
plt.title("NDVI Histogram")
plt.show()

min_display_ndvi = 0.5
max_display_ndvi = 0.92
masked_ndvi = np.ma.masked_where(ndvi < min_display_ndvi, ndvi)
plotutils.plot_overlay_withcolorbar(gamma_corr_rgb, 
                                    masked_ndvi, 
                                    figsize = (18,18), 
                                    title = 'NDVI filtered to only plants over RGB base layer',
                                    vmin = min_display_ndvi,
                                    vmax = max_display_ndvi)


# ## NDRE Computation
# 
# In the same manner, we can compute, filter, and display another index useful for the RedEdge camera, the Normalized Difference Red Edge (NDRE) index.  We also filter out shadows and soil to ensure our display focuses only on the plant health.

# In[ ]:


# Compute Normalized Difference Red Edge Index from the NIR(3) and RedEdge(4) bands
ndre = (im_aligned[:,:,3] - im_aligned[:,:,4]) / (im_aligned[:,:,3] + im_aligned[:,:,4])

# Mask areas with low NDRE and low NDVI
masked_ndre = np.ma.masked_where(ndvi < 0.5, ndre)

# Compute a histogram
hist_min = np.min(masked_ndre[np.where(np.logical_and(masked_ndre > 0, masked_ndre < 1))])
hist_max = np.max(masked_ndre[np.where(np.logical_and(masked_ndre > 0, masked_ndre < 1))])
fig, axis = plt.subplots(1, 1, figsize=(10,4))
axis.hist(masked_ndre.ravel(), bins=512, range=(hist_min, hist_max))
plt.title("NDRE Histogram (filtered to only plants)")
plt.show()

min_display_ndre = 0.05
max_display_ndre = 0.50

plotutils.plot_overlay_withcolorbar(gamma_corr_rgb, 
                                    masked_ndre, 
                                    figsize=(18,18), 
                                    title='NDRE filtered to only plants over RGB base layer',
                                    vmin=min_display_ndre,vmax=max_display_ndre)


# ## Red vs NIR Reflectance
# 
# Finally, we show a classic agricultural remote sensing output in the tassled cap plot.  This plot can be useful for visualizing row crops and plots the Red Reflectance channel on the X-axis against the NIR reflectance channel on the Y-axis. This plot also clearly shows the line of the soil in that space.  The tassled cap view isn't very useful for this orchard data set; however, we can see the "badge of trees" of high NIR reflectance and relatively low red reflectance. This provides an example of one of the uses of aligned images for single capture analysis.

# In[ ]:


fig = plt.figure(figsize=(12,12))
plt.hexbin(im_aligned[:,:,2],im_aligned[:,:,3],gridsize=640,bins='log',extent=(0,0.4,0,0.9))
ax = fig.gca()
ax.set_xlim([0,0.4])
ax.set_ylim([0,0.9])
plt.xlabel("Red Reflectance")
plt.ylabel("NIR Reflectance")
plt.show()


# ---
# Copyright (c) 2017-2018 MicaSense, Inc.  For licensing information see the [project git repository](https://github.com/micasense/imageprocessing)
