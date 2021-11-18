import os
from flask import (
    Flask, flash, render_template, 
    redirect, request, session, url_for)
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
if os.path.exists("env.py"):
    import env

# ---- CONFIG ---- #

app = Flask(__name__)
app.config["MONGO_DBNAME"] = os.getenv(
    "MONGO_DBNAME")
app.config["MONGO_URI"] = os.getenv(
    "MONGO_URI")
app.secret_key = os.getenv(
    "SECRET_KEY")

mongo = PyMongo(app)

# ---- Recipe ---- #


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/get_recipe")
def get_recipe():
    recipe = list(mongo.db.recipe.find())
    return render_template("recipes.html", recipe=recipe)


@app.route("/search", methods=["GET", "POST"])
def search():
    query = request.form.get("query")
    recipe = list(mongo.db.recipe.find({"$text": {"$search": query}}))
    return render_template("recipes.html", recipe=recipe)

# ---- User ---- #


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # check if username already exists in db
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})

        if existing_user:
            flash("Username already exists")
            return redirect(url_for("register"))

        register = {
            "username": request.form.get("username").lower(),
            "password": generate_password_hash(request.form.get("password"))
        }
        mongo.db.users.insert_one(register)

        # put the new user into 'session' cookie
        session["user"] = request.form.get("username").lower()
        flash("Registration Successful!")
        return redirect(url_for("profile", username=session["user"]))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # check if username exists in db
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})

        if existing_user:
            # ensure hashed password matches user input
            if check_password_hash(
                    existing_user["password"], request.form.get("password")):
                        session["user"] = request.form.get("username").lower()
                        flash("Welcome, {}".format(
                            request.form.get("username")))
                        return redirect(url_for(
                            "profile", username=session["user"]))
            else:
                # invalid password match
                flash("Incorrect Username and/or Password")
                return redirect(url_for("login"))

        else:
            # username doesn't exist
            flash("Incorrect Username and/or Password")
            return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/profile/<username>", methods=["GET", "POST"])
def profile(username):
    # grab the session user's username from db
    username = mongo.db.users.find_one(
        {"username": session["user"]})["username"]

    if session["user"]:    
        return render_template("profile.html", username=username)

    return redirect(url_for("login"))


@app.route("/logout")
def logout():
    # remove user from session cookies
    flash("You have now been logged out")
    session.pop("user")
    return redirect(url_for("login"))

# ---- RECIPE PAGES ---- #


@app.route('/recipe_page/<recipe_id>', methods=['GET', 'POST'])
def recipe_page(recipe_id):
    # Route to show single recipe view page
    recipe = mongo.db.recipe.find_one({"_id": ObjectId(recipe_id)})
    recipe_ingredients = recipe['recipe_ingredients'].split(", ")
    comments = mongo.db.comments.find()
    return render_template('recipe.html', recipe=recipe, recipe_ingredients=recipe_ingredients, comments=comments)


@app.route("/add_recipe", methods=["GET", "POST"])
def add_recipe():
    if request.method == "POST":
        add = {
            "category_name": request.form.get("category_name"),
            "recipe_name": request.form.get("recipe_name"),
            "recipe_description": request.form.get("recipe_description"),
            "recipe_ingredients": request.form.get("recipe_ingredients"),
            "recipe_image": request.form.get("recipe_image"),
            "recipe_servings": request.form.get("recipe_servings"),
            "recipe_time": request.form.get("recipe_time"),
            "recipe_method": request.form.get("recipe_method"),
            "created_by": session["user"]
        }
        mongo.db.recipe.insert_one(add)
        flash("Your new recipe is added!")
        return redirect(url_for("get_recipe"))

    categories = mongo.db.categories.find().sort("category_name", 1)
    return render_template("add_recipe.html", categories=categories)


@app.route("/edit_recipe/<recipe_id>", methods=["GET", "POST"])
def edit_recipe(recipe_id):
    if request.method == "POST":
        submit = {
            "category_name": request.form.get("category_name"),
            "recipe_name": request.form.get("recipe_name"),
            "recipe_description": request.form.get("recipe_description"),
            "recipe_ingredients": request.form.get("recipe_ingredients"),
            "recipe_image": request.form.get("recipe_image"),
            "recipe_servings": request.form.get("recipe_servings"),
            "recipe_time": request.form.get("recipe_time"),
            "recipe_method": request.form.get("recipe_method"),
            "created_by": session["user"]
        }
        mongo.db.recipe.update({"_id": ObjectId(recipe_id)}, submit)
        flash("Your recipe is updated!")
        return redirect(url_for("get_recipe"))

    """A dummy docstring."""
    recipe = mongo.db.recipe.find_one({"_id": ObjectId(recipe_id)})
    categories = mongo.db.categories.find().sort("category_name", 1)
    return render_template("edit_recipe.html", recipe=recipe, categories=categories)


@app.route("/delete_recipe/<recipe_id>")
def delete_recipe(recipe_id):
    mongo.db.recipe.remove({"_id": ObjectId(recipe_id)})
    flash("Your recipe is now deleted")
    return redirect(url_for("get_recipe"))


# Add comment 
@app.route("/add-comment/<recipe_id>", methods=["GET", "POST"])
def add_comment(recipe_id):
    # Get the id of the recipe one want to comment
    recipe = mongo.db.recipe.find_one({"_id": ObjectId(recipe_id)})
    if request.method == "POST": 
        # Comment saved in the correct format for comments table
        new_comment = {
            "title": recipe["title"],
            "comment": request.form.get("comment"),
            "username": session["user"]
        }
        # New comment added to comments table
        mongo.db.comments.insert_one(new_comment)
        flash("Your comment is added!")

    return render_template("add-comment.html", recipe=recipe)


# Update comment
@app.route("/update-comment/<comment_id>", methods=["GET", "POST"])
def update_comment(comment_id):
    comments = mongo.db.comments.find_one({"_id": ObjectId(comment_id)})
    if request.method == "POST":
        # Comment found by id updated by new comment
        mongo.db.comments.update({'_id': ObjectId(comment_id)}, {
            "title": comments["title"],
            "comment": request.form.get("comment"),
            "username": session["user"]
        })
        flash("Your comment is updated")
    return render_template("update-comment.html", comments=comments)


# Delete comment
@app.route("/delete-comment<comment_id>", methods=["GET", "POST"])
def delete_comment(comment_id):
    # Removing the comment using the comment id
    mongo.db.comments.remove({"_id": ObjectId(comment_id)})
    flash("Your comment is deleted")
    return redirect(url_for("recipes.html"))


if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=True)