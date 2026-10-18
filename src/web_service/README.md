- Create virtual env using uv
- Creating a script for predicting
- Putting the script into a flask app
- Packaging the app to Docker

# Create virtual environment using uv
The web service gets its own small environment separated from the main one used for training. 

In the `src/web_service` folder run to create the separate venv

```bash
uv init --bare --no-workspace --python 3.14
```
Then add the dependencies

```bash
uv add <dependencies> flask gunicorn
```
We will use both flask and gunicorn (for the production ready server).