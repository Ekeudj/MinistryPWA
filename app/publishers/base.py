from abc import ABC, abstractmethod

class BasePublisher(ABC):
    """
    The master blueprint for all social media publishers.
    Ensures both TikTok and YouTube handle uploads the exact same way.
    """

    @abstractmethod
    def authenticate(self) -> bool:
        """
        Checks if the platform account is active and connected.
        Must return True if authenticated, False if not.
        """
        pass

    @abstractmethod
    def publish_video(self, video_path: str, title: str, description: str, **kwargs) -> dict:
        """
        Handles uploading the video directly to the platform.
        
        :param video_path: Location of the rendered MP4 video on your server.
        :param title: Video Title or Caption.
        :param description: Video description/tags.
        :return: A dictionary showing success or failure status.
        """
        pass