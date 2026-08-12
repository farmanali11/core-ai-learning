# Roadmap to Becoming a Generative AI & Agentic AI Developer

This is my personal roadmap. I'm sharing it so other learners can follow 
the same path, and so I can track my own progress as well.

## 1. Installation and Setup

### What you'll set up
A clean Python environment for Machine Learning, using Miniconda + VSCode.

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

### Step 5 — Set up VSCode
1. Open VSCode
2. Install these extensions:
   - **Python**
   - **Jupyter**

### Step 6 — Create your first notebook
1. Create a new file named `first.ipynb`
   *(`.ipynb` = Interactive Python Notebook)*
2. Select the kernel → choose the **ML** conda environment you created
3. Add a code cell, write any simple Python code, and run it to confirm the output appears

###  You're ready
If the output shows up correctly, your environment is set up and ready for ML development.
## 2. Python

###  Resources I used
- [Python from Beginner to Advanced (Playlist)](https://youtube.com/playlist?list=PLwgFb6VsUj_lQTpQKDtLXKXElQychT_2j&si=UhjL7ieGs-_VBcb_)
- [Practice Exercises – w3resource](https://www.w3resource.com/python-exercises/)


-  Basics — syntax, variables, strings, operators
-  Control flow — conditionals, loops
-  Data structures — lists, tuples, dicts, sets
-  Comprehensions — list, dict, set
-  Functions — args/kwargs, lambda, closures, decorators, generators
-  OOP — classes, inheritance, polymorphism, encapsulation
-  Error handling — try/except, custom exceptions
-  File I/O — text files, CSV
-  OS module & working with files

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
- Browser automation and scraping dynamic (JS-rendered) websites

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
[Playlist](https://www.youtube.com/watch?v=-TYSM0CDA4c&t=1s)
[Docs](https://numpy.org/doc/stable/user/absolute_beginners.html)

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
[Video](https://youtu.be/QUaSmqBeR9w?si=3l6P0UgDPUIHPAW2) 
[Docs](https://pandas.pydata.org/docs/getting_started/index.html)

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

## 7. Advanced Models & Libraries (Widely used in production)
- XGBoost Status: 
[Intro](https://youtu.be/C6aDw4y8qJ0?si=PMQ9XbWm6k9B3H-Y)
[TimeSeries with xgboost](https://youtu.be/vV12dGe_Fho?si=dYj0ykZ3qxJ42kUp)
[Advance Methodsxgboost in ](https://youtu.be/z3ZnOW-S550?si=NY1BtnKxjybIrAUA)
[blog-complete guide](https://mbrenndoerfer.com/writing/xgboost-extreme-gradient-boosting-complete-guide-mathematical-foundations-python-implementation#visualizing-xgboost)
- LightGBM
- CatBoost [Difference blog post](https://apxml.com/posts/xgboost-vs-lightgbm-vs-catboost)
- Time Series Analysis 
- Optuna [Video](https://youtu.be/E2b3SKMw934?si=Zs76L0bxGkJOcDyy)
- XAI
- SHAP [Blog Intro and Implementation](https://machinelearningmastery.com/a-gentle-introduction-to-shap-for-tree-based-models/)  🟢 In Progress
- LIME

---
