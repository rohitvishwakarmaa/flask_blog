from flask import Flask, render_template, request, session
from flask_sqlalchemy import SQLAlchemy
import os
from werkzeug.utils import secure_filename
from datetime import datetime
from flask import redirect, url_for
import json
import math

with open('config.json', 'r') as c:
    params = json.load(c)["params"]

local_server = True
app = Flask(__name__)
app.secret_key = 'super-secret-key'
app.config['UPLOAD_FOLDER'] = params['upload_location']

if local_server:
    app.config['SQLALCHEMY_DATABASE_URI'] = params['local_uri']
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = params['prod_uri']

db = SQLAlchemy(app)

class Contacts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    phone_num = db.Column(db.String(12), nullable=False)
    msg = db.Column(db.String(80), nullable=False)
    date = db.Column(db.String(12), nullable=True)
    email = db.Column(db.String(120), nullable=False)

class Posts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), nullable=False)
    slug = db.Column(db.String(21), nullable=False)
    content = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(12), nullable=True)
    tagline = db.Column(db.String(12), nullable=True)
    img_file = db.Column(db.String(12), nullable=True)


@app.route("/")
def home():
    posts = Posts.query.filter_by().all()
    last = math.ceil(len(posts) / int(params['no_of_posts']))
    page = request.args.get('page')

    if not str(page).isnumeric():
        page = 1

    page = int(page)
    start = (page - 1) * int(params['no_of_posts'])
    end = start + int(params['no_of_posts'])
    posts = posts[start:end]

    if page == 1:
        prev = "#"
        next = "/?page=" + str(page + 1)
    elif page == last:
        prev = "/?page=" + str(page - 1)
        next = "#"
    else:
        prev = "/?page=" + str(page - 1)
        next = "/?page=" + str(page + 1)

    return render_template('index.html', params=params, posts=posts, prev=prev, next=next)

@app.route("/post/<string:post_slug>/", methods=['GET'])
def post_route(post_slug):
    post = Posts.query.filter_by(slug=post_slug).first()
    return render_template('post.html', params=params, post=post)

@app.route("/about")
def about():
    return render_template('about.html', params=params)

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user" in session and session['user'] == params['admin_user']:
        posts = Posts.query.all()
        return render_template("dashboard.html", params=params, posts=posts)

    if request.method == "POST":
        username = request.form.get("uname")
        userpass = request.form.get("pass")
        if username == params['admin_user'] and userpass == params['admin_password']:
            session['user'] = username
            posts = Posts.query.all()
            return render_template("dashboard.html", params=params, posts=posts)
        else:
            return render_template("login.html", params=params, error="Invalid credentials")

    return render_template("login.html", params=params)

@app.route("/posts", methods=['GET'])
def all_posts():
    page = request.args.get('page', 1, type=int)
    posts = Posts.query.paginate(page=page, per_page=5)
    return render_template('allpost.html', params=params, posts=posts.items, pagination=posts)

@app.route("/uploader", methods=['GET', 'POST'])
def uploader():
    if "user" in session and session['user'] == params['admin_user']:
        if request.method == 'POST':
            f = request.files['file1']
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(f.filename)))
            return "Uploaded successfully!"
    return redirect('/dashboard')

@app.route("/delete/<string:sno>", methods=['GET', 'POST'])
def delete(sno):
    if "user" in session and session['user'] == params['admin_user']:
        post = Posts.query.filter_by(sno=sno).first()
        db.session.delete(post)
        db.session.commit()
    return redirect("/dashboard")

@app.route('/logout')
def logout():
    session.pop('user')
    return redirect('/dashboard')

@app.route("/contact", methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        message = request.form.get('message')

        entry = Contacts(name=name, phone_num=phone, msg=message, email=email)
        db.session.add(entry)
        db.session.commit()

    return render_template('contact.html', params=params)



@app.route("/edit/<string:sno>", methods=['GET', 'POST'])
def edit(sno):
    if "user" in session and session['user'] == params['admin_user']:
        if request.method == "POST":
            box_title = request.form.get('title')
            tline = request.form.get('tline')
            slug = request.form.get('slug')
            content = request.form.get('content')
            img_file = request.form.get('img_file')
            date = datetime.now()

            if sno == '0':
                # Creating a new post with auto-incremented sno
                post = Posts(title=box_title, slug=slug, content=content, tagline=tline, img_file=img_file, date=date)
                db.session.add(post)
                try:
                    db.session.commit()
                    return redirect('/dashboard')
                except Exception as e:
                    db.session.rollback()
                    print(f"Error while adding post: {e}")
                    return "An error occurred while adding the post."
            else:
                # Editing an existing post
                post = Posts.query.filter_by(sno=sno).first()
                if post:
                    post.title = box_title
                    post.tagline = tline
                    post.slug = slug
                    post.content = content
                    post.img_file = img_file
                    post.date = date
                    try:
                        db.session.commit()
                        return redirect('/edit/' + sno)
                    except Exception as e:
                        db.session.rollback()
                        print(f"Error while updating post: {e}")
                        return "An error occurred while updating the post."
                else:
                    return "Post not found."

    # Fetch post for editing if sno is not '0'
    post = Posts.query.filter_by(sno=sno).first() if sno != '0' else None
    return render_template('edit.html', params=params, post=post)

if __name__ == '__main__':
    app.run(debug=True)
