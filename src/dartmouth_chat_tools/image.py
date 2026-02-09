import json
import logging

from fastapi import Request

from open_webui.models.users import UserModel

from open_webui.routers.images import (
    image_generations,
    image_edits,
    CreateImageForm,
    EditImageForm,
)
from open_webui.models.chats import Chats

log = logging.getLogger(__name__)


class Tools:
    # =============================================================================
    # IMAGE GENERATION TOOLS
    # =============================================================================

    async def generate_image(
        self,
        prompt: str,
        __request__: Request = None,
        __user__: dict = None,
        __event_emitter__: callable = None,
        __chat_id__: str = None,
        __message_id__: str = None,
    ) -> str:
        """
        Generate an image based on a text prompt.

        :param prompt: A detailed description of the image to generate
        :return: Confirmation that the image was generated, or an error message
        """
        if __request__ is None:
            return json.dumps({"error": "Request context not available"})

        try:
            user = UserModel(**__user__) if __user__ else None

            images = await image_generations(
                request=__request__,
                form_data=CreateImageForm(prompt=prompt),
                user=user,
            )

            # Prepare file entries for the images
            image_files = [{"type": "image", "url": img["url"]} for img in images]

            # Persist files to DB if chat context is available
            if __chat_id__ and __message_id__ and images:
                image_files = Chats.add_message_files_by_id_and_message_id(
                    __chat_id__,
                    __message_id__,
                    image_files,
                )

            # Emit the images to the UI if event emitter is available
            if __event_emitter__ and image_files:
                await __event_emitter__(
                    {
                        "type": "chat:message:files",
                        "data": {
                            "files": image_files,
                        },
                    }
                )
                # Return a message indicating the image is already displayed
                return json.dumps(
                    {
                        "status": "success",
                        "message": "The image has been successfully generated and is already visible to the user in the chat. You do not need to display or embed the image again - just acknowledge that it has been created.",
                        "images": images,
                    },
                    ensure_ascii=False,
                )

            return json.dumps(
                {"status": "success", "images": images}, ensure_ascii=False
            )
        except Exception as e:
            log.exception(f"generate_image error: {e}")
            return json.dumps({"error": str(e)})

    async def edit_image(
        self,
        prompt: str,
        image_urls: list[str],
        __request__: Request = None,
        __user__: dict = None,
        __event_emitter__: callable = None,
        __chat_id__: str = None,
        __message_id__: str = None,
    ) -> str:
        """
        Edit existing images based on a text prompt.

        :param prompt: A description of the changes to make to the images
        :param image_urls: A list of URLs of the images to edit
        :return: Confirmation that the images were edited, or an error message
        """
        if __request__ is None:
            return json.dumps({"error": "Request context not available"})

        try:
            user = UserModel(**__user__) if __user__ else None

            images = await image_edits(
                request=__request__,
                form_data=EditImageForm(prompt=prompt, image=image_urls),
                user=user,
            )

            # Prepare file entries for the images
            image_files = [{"type": "image", "url": img["url"]} for img in images]

            # Persist files to DB if chat context is available
            if __chat_id__ and __message_id__ and images:
                image_files = Chats.add_message_files_by_id_and_message_id(
                    __chat_id__,
                    __message_id__,
                    image_files,
                )

            # Emit the images to the UI if event emitter is available
            if __event_emitter__ and image_files:
                await __event_emitter__(
                    {
                        "type": "chat:message:files",
                        "data": {
                            "files": image_files,
                        },
                    }
                )
                # Return a message indicating the image is already displayed
                return json.dumps(
                    {
                        "status": "success",
                        "message": "The edited image has been successfully generated and is already visible to the user in the chat. You do not need to display or embed the image again - just acknowledge that it has been created.",
                        "images": images,
                    },
                    ensure_ascii=False,
                )

            return json.dumps(
                {"status": "success", "images": images}, ensure_ascii=False
            )
        except Exception as e:
            log.exception(f"edit_image error: {e}")
            return json.dumps({"error": str(e)})
