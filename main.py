from fastapi import FastAPI
from typing import Optional
from blog_app.schemas.schemas import BlogPost


app = FastAPI()



app.post("/blog/create_blog_post")
def create_blog_post(blog_post: BlogPost):
    return {
        "message": "Blog post created successfully",
        "blog_post": blog_post
    }