"""
Elastic Beanstalk entry point
This file is required by AWS Elastic Beanstalk
"""
from app import app as application

if __name__ == "__main__":
    application.run()
