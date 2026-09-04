# Roadmap to Becoming a Generative AI & Agentic AI Developer

This is my personal roadmap for learning AI. I'm sharing it so other learners can follow the same path, get a complete roadmap with resources, and also because I'm tracking my own progress here.

I will update this as I go. Some weeks I will cover a lot, some weeks barely anything — and that's fine. I want this to be honest than perfect.

Regards  
**Farman**

---

## 1. Installation and Setup

### What You Will Set Up

A clean Python environment for machine learning using Miniconda and VS Code.

### Step 1 — Install Miniconda

Download and install Miniconda from the [official site](https://docs.conda.io/en/latest/miniconda.html).

### Step 2 — Create a virtual environment

Open a terminal and run:
```bash
conda create -n ML python=3.11
```

### Step 3 — Activate the environment

```bash
conda activate ML
```

### Step 4 — Install core libraries

```bash
pip install numpy pandas matplotlib seaborn scikit-learn
```

### Step 5 — Set Up VS Code

1. Open VS Code.
2. Install these extensions:
   - **Python**
   - **Jupyter**

### Step 6 — Create your first notebook
1. Create a new file named `first.ipynb`.
   *(`.ipynb` = Interactive Python Notebook)*
2. Select the kernel and choose the **ML** conda environment you created.
3. Add a code cell, write simple Python code, and run it to confirm that the output appears.

### You Are Ready
If the output appears correctly, your environment is ready for machine learning development.

## 2. Python

### Resources
- [Python from Beginner to Advanced (Playlist)](https://youtube.com/playlist?list=PLwgFb6VsUj_lQTpQKDtLXKXElQychT_2j&si=UhjL7ieGs-_VBcb_)
- [Practice Exercises – w3resource](https://www.w3resource.com/python-exercises/)


- Basics — syntax, variables, strings, and operators
- Control flow — conditionals and loops
- Data structures — lists, tuples, dictionaries, and sets
- Comprehensions — list, dictionary, and set comprehensions
- Functions — arguments, keyword arguments, lambdas, closures, decorators, and generators
- Object-oriented programming — classes, inheritance, polymorphism, and encapsulation
- Error handling — `try`/`except` and custom exceptions
- File I/O — text files and CSV
- The `os` module and file handling

📄 Full breakdown: [python.md](python.md)



## 3. Parallel Programming

### Resources
- [Playlist 1](https://www.youtube.com/playlist?list=PL8gkFND9Wl5P5SA-DQwNdm-HODAQc8-cX)
- [Playlist 2](https://www.youtube.com/playlist?list=PL8gkFND9Wl5P5SA-DQwNdm-HODAQc8-cX)
- [SuperFastPython Docs](https://superfastpython.com/tutorial-archive.html#concurrent-file-i-o)

### Topics Covered So Far
- Thread basics
- Thread data
- Race conditions
- Deadlocks
- Producer-consumer model
- Python GIL (Global Interpreter Lock)
- Multiprocessing
- `concurrent.futures`
- Introduction to async and await
- `aiohttp`
- `aiofiles`


## 4. Data Scraping

### Resources
- [Playlist – Web Scraping Basics](https://youtu.be/XVv6mJpFOb0?si=bp_x8kG9YTyAqdHv)
- [BeautifulSoup4 Docs](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)

### Topics and Libraries Covered

**BeautifulSoup (BS4)**
- Parsing HTML and extracting data

**Playwright**
- Resources:
[Playlist](https://www.youtube.com/playlist?list=PLhW3qG5bs-L8WcAa9cfXaqGe0-Cq85y4X) 
[Docs](https://playwright.dev/python/docs/intro)
- Browser automation and scraping dynamic (JavaScript-rendered) websites

**Playwright Stealth**
- Resource: [GitHub – playwright-stealth](https://github.com/Granitosaurus/playwright-stealth)
- Avoiding bot-detection while scraping

**Scrapling**
- Docs: [scrapling.readthedocs.io](https://scrapling.readthedocs.io/en/latest/index.html)

**Scrapy**
- Resources:
[Video](https://www.youtube.com/watch?v=mBoX_JCKZTE)
[Docs](https://docs.scrapy.org/en/latest/)
- Building scalable scraping spiders/pipelines

---

## 5. Data Analysis

### NumPy
**Resources:** 
[Playlist](https://www.youtube.com/watch?v=-TYSM0CDA4c&t=1s) · [Documentation](https://numpy.org/doc/stable/user/absolute_beginners.html)

- Introduction to NumPy arrays (ndarray)
- Creating arrays — `array()`, `zeros()`, `ones()`, `full()`, `arange()`, `linspace()`
- Array attributes — shape, size, dtype, ndim
- Indexing and slicing
- Reshaping arrays — `reshape()`, `flatten()`, `ravel()`
- Stacking and splitting arrays — `vstack()`, `hstack()`, `split()`
- Array math operations (element-wise +, -, *, /)
- Broadcasting
- Aggregate functions — `sum()`, `mean()`, `median()`, `std()`, `var()`, `min()`, `max()`
- Sorting arrays
- Boolean indexing and filtering
- Fancy indexing
- Copy vs view
- Random module — `random.rand()`, `random.randint()`, `random.seed()`
- Linear algebra basics — dot product, matrix multiplication, transpose
- Working with `NaN` and `inf`

---

### Pandas
**Resources:**
[Video](https://youtu.be/QUaSmqBeR9w?si=3l6P0UgDPUIHPAW2) · [Documentation](https://pandas.pydata.org/docs/getting_started/index.html)

- Pandas Series
- DataFrames
- Handling missing data
- Merging data
- Joining data
- Concatenation
- Groupby
- Aggregation
- Pivot tables
- Common operations
- Data exploration / findings
- Feature extraction
- Capstone project

---

### Matplotlib
**Resources:** [Playlist](https://youtube.com/playlist?list=PLjVLYmrlmjGcC0B_FP3bkJ-JIPkV5GuZR&si=n5Saavz5xN4Wy0HG) · [Docs](https://matplotlib.org/stable/index.html)

- Bar plot
- Scatter graph
- Histogram
- Stem plot
- Subplot
- Save figure (`savefig`)
- Fill between
- Step plot
- Axis customization
- Area plot
- Pie chart


## 6. Machine Learning  (Foundational Models Covered)

###  Resources I used
1. **Playlist:** [YouTube Live Series](https://www.youtube.com/live/7z8-QWlbmoo?si=tqkub8GIj3hyrpM0)
2. **IBM & DataCamp** — Search each model name on Google along with "IBM" or 
   "DataCamp." They explain models in a simple, easy-to-understand way. 
   Do this *before* going to the official Scikit-learn docs — the docs can 
   be hard to follow if you don't have the basics first.
3. **Scikit-learn Official Docs** — Use these after the above, for both 
   classification and regression models.

###  Models covered
- KNN
- SVM
- Linear Regression
- Logistic Regression
- K-Means Clustering
- Naive Bayes
- Decision Tree
- Random Forest
- AdaBoost
- Gradient Boosting
- GridSearchCV
- RandomizedSearchCV
- Mean Shift
- Ensemble Learning
- DBSCAN
- Applied all of the above on a real production-style dataset (project)

## 7. Advanced Models and Libraries (Widely Used in Production)
- XGBoost
[Intro](https://youtu.be/C6aDw4y8qJ0?si=PMQ9XbWm6k9B3H-Y)
[TimeSeries with xgboost](https://youtu.be/vV12dGe_Fho?si=dYj0ykZ3qxJ42kUp)
[Advance Methodsxgboost in ](https://youtu.be/z3ZnOW-S550?si=NY1BtnKxjybIrAUA)
[blog-complete guide](https://mbrenndoerfer.com/writing/xgboost-extreme-gradient-boosting-complete-guide-mathematical-foundations-python-implementation#visualizing-xgboost)
- LightGBM [official Docs](https://lightgbm.readthedocs.io/en/stable/) -- [other](https://www.geeksforgeeks.org/machine-learning/lightgbm-light-gradient-boosting-machine/)
- CatBoost [Difference blog post](https://apxml.com/posts/xgboost-vs-lightgbm-vs-catboost)
- Time-Series Analysis
- Optuna [Video](https://youtu.be/E2b3SKMw934?si=Zs76L0bxGkJOcDyy)
- XAI
- SHAP [Blog Intro and Implementation](https://machinelearningmastery.com/a-gentle-introduction-to-shap-for-tree-based-models/)
- LIME [Shap vs Lime](https://apxml.com/posts/lime-vs-shap-difference-interpretability)

---

## 8. Introduction to Deep Learning (Theory-Focused)
### MIT 2026
[Resources - Playlist](https://youtube.com/playlist?list=PLtBw6njQRU-rwp5__7C0oIVt26ZgjG9NI&si=ed8i0eSRabxWCvbz)

- Setting Up
- Deep Learning Introduction
- The Perceptron
- Common Functions
- Deep Neural Network
- Quantifying loss, empirical loss, and binary cross-entropy loss
- Training Neural Networks
- Regularization
- RNNs
- CNNs
- RCNN
- FCN
- Generative Modeling
- Latent Variable
- AutoEncoders
- VAEs
- GANs
- Deep Reinforcement Learning
- DQN
- Neural Network Limitations

## 9. Transformer Architecture

- What Are Transformers?
- *Attention Is All You Need* — research paper
- Self-Attention
- Multi-Head Attention
- Positional Encoding
- Layer Normalization
- Masked Self Attention
- Cross Attention
- Transformers During Training and Inference

## 10. Diffusion Model Architecture


- Diffusion Introduction: Forward and Reverse Processes
- *High-Resolution Image Synthesis with Latent Diffusion* — research paper
- Latent/Stable Diffusion
- Adversarial Loss
- Perceptual Loss
- U-Net Architecture
- Unconditional Latent Diffusion
- Conditional Latent Diffusion Models
- Text-to-Image
- Image-to-Image
- ControlNet

## 11. Deep Learning with TensorFlow and Keras (Implementation-Focused)

**Note:** Switched to Colab for now, mainly for free T4 GPU. My VS Code setup was way smoother and I was comfortable with it as well, but Colab is something I will have to get comfortable one day — so why not start today.

**Resources**

- [Playlist](https://youtube.com/playlist?list=PLeo1K3hjS3uu7CxAacxVndI4bE_o3BDtO&si=1x5DbARHzH3ZE1dC)
- [Docs](https://keras.io/getting_started/intro_to_keras_for_engineers/)

**Topics**

- Introduction
- PyTorch vs. TensorFlow vs. Keras
- Neural network for handwritten-digit classification
- Activation functions

---










