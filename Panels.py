
# coding: utf-8

# # Panels
# This notebook shows usage for the Panel class.  This type is useful for detecting MicaSense calibration panels and extracting information about the lambertian panel surface.

# In[ ]:


import os, glob
from micasense.image import Image
from micasense.panel import Panel
get_ipython().run_line_magic('matplotlib', 'inline')

imagePath = os.path.join('.','data','0000SET','000')
imageName = glob.glob(os.path.join(imagePath,'IMG_0000_1.tif'))[0]

img = Image(imageName)
panel = Panel(img)

if not panel.panel_detected():
    raise IOError("Panel Not Detected!")
    
print("Detected panel serial: {}".format(panel.serial))
mean, std, num, sat_count = panel.raw()
print("Extracted Panel Statistics:")
print("Mean: {}".format(mean))
print("Standard Deviation: {}".format(std))
print("Panel Pixel Count: {}".format(num))
print("Saturated Pixel Count: {}".format(sat_count))

panel.plot();


# ---
# Copyright (c) 2017-2018 MicaSense, Inc.  For licensing information see the [project git repository](https://github.com/micasense/imageprocessing)
