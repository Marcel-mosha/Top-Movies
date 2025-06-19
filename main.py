from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
import requests
import os
from dotenv import load_dotenv
from urllib.parse import quote

load_dotenv()
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("FLASK_KEY")
Bootstrap5(app)
api_key = os.environ.get("API_KEY")
movie_endpoint = os.environ.get("MOVIE_ENDPOINT")
movie_db_img_url = "https://image.tmdb.org/t/p/w500"
db_user = os.environ.get("DB_USER")
database = os.environ.get("DB")
db_password = quote(os.environ.get("DB_PASSWORD"))
db_port = os.environ.get("DB_PORT")
db_host = os.environ.get("DB_HOST")


class MovieForm(FlaskForm):
    rating = StringField("Your rating out of 10 e.g 7.5",
                         validators=[DataRequired()])
    review = StringField("Your review", validators=[DataRequired()])
    submit = SubmitField("Done")


class AddMovieForm(FlaskForm):
    title = StringField("Movie Title", validators=[DataRequired()])
    submit = SubmitField("Add Movie")


class Base(DeclarativeBase):
    pass


app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{database}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(model_class=Base)
db.init_app(app)


class Movie(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    rating: Mapped[float] = mapped_column(Float, nullable=True)
    ranking: Mapped[int] = mapped_column(Integer, nullable=True)
    review: Mapped[str] = mapped_column(String(250), nullable=True)
    img_url: Mapped[str] = mapped_column(String, nullable=False)


with app.app_context():
    db.create_all()


@app.route("/")
def home():
    # Sort movies by rating in descending order
    result = db.session.execute(db.select(Movie).order_by(Movie.rating.desc()))
    all_movies = result.scalars().all()

    # Assign rankings based on the sorted order
    for i, movie in enumerate(all_movies, start=1):
        movie.ranking = i
    db.session.commit()

    return render_template("index.html", movies=all_movies)


@app.route("/add", methods=["POST", "GET"])
def add_movie():
    form = AddMovieForm()
    if form.validate_on_submit():
        params = {
            "api_key": api_key,
            "query": form.title.data
        }

        response = requests.get(movie_endpoint, params=params).json()["results"]
        return render_template("select.html", choices=response)
    return render_template("add.html", form=form)


@app.route("/edit", methods=['POST', 'GET'])
def edit():
    form = MovieForm()
    movie_id = request.args.get("id")
    movie_selected = db.get_or_404(Movie, movie_id)
    if form.validate_on_submit():
        movie_selected.rating = float(form.rating.data)
        movie_selected.review = form.review.data
        db.session.commit()
        return redirect(url_for('home'))
    return render_template("edit.html", movie=movie_selected, form=form)


@app.route("/delete")
def delete():
    movie_id = request.args.get('id')

    # DELETE A RECORD BY ID
    movie_to_delete = db.get_or_404(Movie, movie_id)
    db.session.delete(movie_to_delete)
    db.session.commit()
    return redirect(url_for('home'))


@app.route('/find')
def find_movie():
    movie_api_id = request.args.get("id")
    if movie_api_id:
        movie_api_url = f"https://api.themoviedb.org/3/movie/{movie_api_id}"
        params = {
            "api_key": api_key,
            "language": "en-US"
        }

        response = requests.get(movie_api_url, params=params).json()
        new_movie = Movie(
            title=response["title"],
            year=response["release_date"].split("-")[0],
            img_url=f"{movie_db_img_url}/{response['poster_path']}",
            description=response["overview"]
        )
        db.session.add(new_movie)
        db.session.commit()
        return redirect(url_for("edit", id=new_movie.id))


if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
