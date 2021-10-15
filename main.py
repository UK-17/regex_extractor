#using FastAPI to extend functionality as a web service
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.routes import router as router


#setting up logger and logging profiles
import logging
logging.config.fileConfig("./logging.conf", disable_existing_loggers=False)
logger = logging.getLogger(__name__)
TRACE_LEVEL_NUM = 9 
logging.addLevelName(TRACE_LEVEL_NUM, "TRACE")
def trace(self, message, *args, **kws):
    self._log(TRACE_LEVEL_NUM, message, args, **kws) 
logging.Logger.trace = trace
PROFILE_LEVEL_NUM = 51
logging.addLevelName(PROFILE_LEVEL_NUM, "PROFILE")
def profile(self, message, *args, **kws):
    self._log(PROFILE_LEVEL_NUM, message, args, **kws) 
logging.Logger.profile = profile


#app to run on startup
app = FastAPI(
	title="regex-extractor",
	description="REST API"
)

#adding configurable middleware
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex='.*',
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count","Content-Range"]
    )

#adding router to the app
app.router.include_router(router, prefix="/parser")

#service startup events
@app.on_event("startup")
def handle_startup():
    logger.info("Initializing Parser.")

    # Add code above this line
    logger.info("Application startup event.")

