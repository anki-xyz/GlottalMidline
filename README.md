# Glottal Midline prediction

For GlottisNet (Kist et al., 2020), a novel multi-task architecture that predicts both, glottis segmentation and glottal midline, we extended the BAGLS dataset (Gómez et al., 2020). Here, we provide the tool we were using to annotate the posterior and anterior point. We further provide the annotations for the training and test dataset in the respective subfolders.

## Using the annotation tool

Execute the annotation tool in your Python environment:

    python annotate.py
    
This tool uses the following dependencies:

- PyQt5
- pyqtgraph
- imageio
- numpy

Please ensure that these dependencies are installed in your local Python environment.

Next, select `File` -> `Open` to select a folder, e.g. the training or the test dataset from BAGLS. If you would like to use our annotations, please download the `ap.points` files from the training or test folder and move them into the respective training or test folder. The annotation tool uses this file to show previous annotations.


## References

Gómez, P., Kist, A. M., Schlegel, P., Berry, D. A., Chhetri, D. K., Dürr, S., ... & Döllinger M. (2020). BAGLS, a multihospital Benchmark for automatic Glottis Segmentation. Scientific data, 7(1), 1-12. https://doi.org/10.1038/s41597-020-0526-3

Kist, A. M., Zilker, J., Gómez, P., Schützenberger, A., & Döllinger, M. (2020). Rethinking glottal midline detection. Scientific Reports, in press.
