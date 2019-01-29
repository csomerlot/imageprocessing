
# coding: utf-8

# In[ ]:


import os, glob
import micasense.capture as capture
get_ipython().run_line_magic('matplotlib', 'inline')

imagePath = os.path.join('.','data','0000SET','000')
imageNames = glob.glob(os.path.join(imagePath,'IMG_0000_*.tif'))

capture = capture.Capture.from_filelist(imageNames)
capture.plot_raw()


# # More Capture visualization functions

# In[ ]:


capture.plot_vignette();
capture.plot_undistorted_radiance();
capture.plot_panels()


# ---
# Copyright (c) 2017 MicaSense, Inc.  For licensing information see the [project git repository](https://github.com/micasense/imageprocessing)
