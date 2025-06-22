# UploadBot/edit_reel.py

import time
from typing import Dict, List, Optional, Tuple

import uiautomator2 as u2

from Shared.instagram_actions import InstagramInteractions  # Assuming path
from Shared.Utils.logger_config import setup_logger  # Assuming path

logger = setup_logger(__name__)


class ReelEditor:
    """
    Provides a flexible interface to apply various edits to an Instagram Reel.
    Each editing capability is exposed as a separate method.
    The calling script is responsible for orchestrating the sequence of edits.
    Assumes the script is already on the reel editing page where options like
    'Add text', 'Effects', 'Stickers', 'Audio', 'Next' are visible.
    """

    def __init__(self, device: u2.Device, insta_actions: InstagramInteractions):
        self.device = device
        self.insta_actions = insta_actions
        self.xpath_config = self.insta_actions.xpath_config

    # --- Private Helper Methods (many can be reused from previous version) ---
    def _find_item_in_horizontal_scrollable(
        self,
        item_name: str,
        scrollable_xpath: str,
        item_xpath_template: str,
        max_swipes: int = 7,
        action_delay: float = 0.5,
    ) -> bool:
        # (Implementation from previous response - finds and clicks item in a H-scroll)
        logger.debug(
            f"Searching for '{item_name}' in scrollable: {scrollable_xpath} using template: {item_xpath_template}"
        )
        target_item_xpath = (
            item_xpath_template  # Assuming template is directly usable or pre-formatted
        )

        for swipe_attempt in range(max_swipes + 1):
            # Check if the specific item exists using its direct XPath
            if self.insta_actions.element_exists(target_item_xpath):
                logger.info(f"Found '{item_name}' at XPath: {target_item_xpath}")
                if self.insta_actions.click_by_xpath(target_item_xpath, timeout=2):
                    time.sleep(action_delay)
                    return True
                else:
                    logger.warning(
                        f"Found '{item_name}' but click failed. Retrying swipe or failing."
                    )

            if swipe_attempt < max_swipes:
                logger.debug(
                    f"'{item_name}' not visible yet. Swiping left on {scrollable_xpath} (Attempt {swipe_attempt + 1}/{max_swipes})"
                )
                scroll_element = self.device.xpath(scrollable_xpath)
                if scroll_element.exists:
                    scroll_element.swipe("left", steps=20)
                    time.sleep(0.8)  # Increased wait for scroll and UI update
                else:
                    logger.warning(
                        f"Scrollable element {scrollable_xpath} not found for swiping."
                    )
                    return False
            else:
                logger.warning(
                    f"Max swipes reached. '{item_name}' not found in {scrollable_xpath}."
                )

        logger.error(
            f"Could not find and click '{item_name}' using template '{item_xpath_template}' after {max_swipes} swipes."
        )
        return False

    # --- Public Editing Methods ---

    def add_text(self, text_config: Dict) -> bool:
        """
        Adds a single block of text with specified formatting.
        Args:
            text_config (Dict): Configuration for the text block, e.g.,
                {
                    "content": "Hello!",
                    "font": "Typewriter",
                    "color": "Red",
                    "animation": "Typewriter",
                    "background_effect": "Sparkle",
                    "alignment": "center"
                }
        Returns:
            bool: True if text was added and formatted successfully, False otherwise.
        """
        logger.info(f"Adding text item: {text_config.get('content', 'No Content')}")

        # 1. Click "Add Text" button on the main editor
        if not self.insta_actions.click_by_xpath(
            self.xpath_config.reel_edit_initial_add_text_button, timeout=5
        ):
            logger.error("Failed to click initial 'Add Text' (Aa) button.")
            return False
        time.sleep(1.5)  # Wait for text input UI to be fully ready

        # 2. Type text
        text_content = text_config.get("content")
        if text_content:
            if not self.insta_actions.input_text(
                self.xpath_config.reel_edit_text_input_field_focused,
                text_content,
                timeout=5,
                clear_first=False,
            ):
                logger.error(f"Failed to type text: {text_content}")
                # Try to click Done to exit text mode if typing fails
                self.insta_actions.click_by_xpath(
                    self.xpath_config.reel_edit_text_tool_done_button, timeout=2
                )
                return False
            time.sleep(0.5)

        # 3. Select Font
        font_name = text_config.get("font")
        if font_name:
            logger.info(f"Setting font to: {font_name}")
            if not self.insta_actions.click_by_xpath(
                self.xpath_config.reel_edit_text_font_category_button, timeout=3
            ):  # Click 'A' icon
                logger.warning(
                    "Could not click font category button in text tool menu."
                )
            else:
                time.sleep(0.5)
                # Assuming font name is the direct text on the button/view in the scroll list
                font_xpath_template = (
                    self.xpath_config.reel_edit_text_font_name_in_list(font_name)
                )  # This method should exist in xpath_config
                if not self._find_item_in_horizontal_scrollable(
                    item_name=font_name,
                    scrollable_xpath=self.xpath_config.reel_edit_text_font_styles_scrollable,
                    item_xpath_template=font_xpath_template,
                ):
                    logger.warning(f"Font '{font_name}' not found or click failed.")
                else:
                    logger.info(f"Successfully selected font: {font_name}")
            time.sleep(0.5)

        # 4. Select Color
        color_name = text_config.get("color")
        if color_name:
            logger.info(f"Setting color to: {color_name}")
            if not self.insta_actions.click_by_xpath(
                self.xpath_config.reel_edit_text_color_category_button, timeout=3
            ):  # Click color wheel icon
                logger.warning(
                    "Could not click color category button in text tool menu."
                )
            else:
                time.sleep(0.5)
                color_xpath = self.xpath_config.reel_edit_text_color_option(
                    color_name
                )  # e.g. "Black color"
                if not self.insta_actions.click_by_xpath(color_xpath, timeout=3):
                    logger.warning(f"Color '{color_name}' not found or click failed.")
                else:
                    logger.info(f"Successfully selected color: {color_name}")
            time.sleep(0.5)

        # 5. Select Text Animation
        animation_name = text_config.get("animation")
        if animation_name:
            logger.info(f"Setting text animation to: {animation_name}")
            if not self.insta_actions.click_by_xpath(
                self.xpath_config.reel_edit_text_animation_icon, timeout=3
            ):  # This is the icon from your list
                logger.warning(
                    "Could not click text animation icon. Skipping animation."
                )
            else:
                time.sleep(0.5)
                animation_xpath_template = (
                    self.xpath_config.reel_edit_text_animation_style_button(
                        animation_name
                    )
                )
                if not self._find_item_in_horizontal_scrollable(
                    item_name=animation_name,
                    scrollable_xpath=self.xpath_config.reel_edit_text_animation_picker_recyclerview,
                    item_xpath_template=animation_xpath_template,
                ):
                    logger.warning(
                        f"Text animation '{animation_name}' not found or click failed."
                    )
                else:
                    logger.info(
                        f"Successfully selected text animation: {animation_name}"
                    )
            time.sleep(0.5)

        # 6. Select Text Background Effect
        background_effect_name = text_config.get("background_effect")
        if background_effect_name:
            logger.info(f"Setting text background effect to: {background_effect_name}")
            if not self.insta_actions.click_by_xpath(
                self.xpath_config.reel_edit_text_background_effect_category_button,
                timeout=3,
            ):
                logger.warning(
                    "Could not click text background effect category button."
                )
            else:
                time.sleep(0.5)
                if (
                    background_effect_name.lower() == "none"
                    or not background_effect_name
                ):
                    target_xpath = self.xpath_config.reel_edit_text_no_effect_button
                    if not self.insta_actions.click_by_xpath(target_xpath, timeout=2):
                        logger.warning(f"Failed to click 'No text effect'.")
                    else:
                        logger.info(f"Successfully selected 'No text effect'.")
                else:
                    effect_xpath_template = (
                        self.xpath_config.reel_edit_text_effect_style_button(
                            background_effect_name
                        )
                    )
                    if not self._find_item_in_horizontal_scrollable(
                        item_name=background_effect_name,
                        scrollable_xpath=self.xpath_config.reel_edit_text_effect_picker_recyclerview,
                        item_xpath_template=effect_xpath_template,
                    ):
                        logger.warning(
                            f"Text background effect '{background_effect_name}' not found or click failed."
                        )
                    else:
                        logger.info(
                            f"Successfully selected text background effect: {background_effect_name}"
                        )
            time.sleep(0.5)

        # 7. Set Text Alignment
        alignment = text_config.get("alignment")
        if alignment:
            logger.info(f"Setting text alignment to: {alignment}")
            alignment_xpath = self.xpath_config.reel_edit_text_alignment_button(
                alignment
            )
            # Alignment often cycles. May need to click until desired state is achieved if not directly selectable.
            # For now, assume direct click works or the provided XPath is for the already-set state which means no click if already aligned.
            # If it's a button that cycles, you'd click it 0, 1, or 2 times.
            if not self.insta_actions.click_by_xpath(
                alignment_xpath, timeout=3
            ):  # Click the specific alignment button
                logger.warning(
                    f"Failed to click text alignment button for '{alignment}'. State might be already correct or button needs cycling."
                )
            else:
                logger.info(f"Text alignment button for {alignment} clicked.")
            time.sleep(0.5)

        # 8. Click "Done" for this text item (to apply it and exit text editing mode)
        if not self.insta_actions.click_by_xpath(
            self.xpath_config.reel_edit_text_tool_done_button, timeout=5
        ):
            logger.error("Failed to click 'Done' button for text item.")
            return False
        logger.info("Text item added and 'Done' clicked.")
        time.sleep(
            1.5
        )  # Wait for text to be placed on reel and UI to return to main edit screen
        return True

    def add_sticker_via_search(self, search_term: str, select_index: int = 0) -> bool:
        """
        Adds a sticker by searching for a term and selecting from results.
        Args:
            search_term (str): The term to search for (e.g., for GIFs).
            select_index (int): 0-based index of the sticker to select from search results.
        Returns:
            bool: True if sticker was added successfully.
        """
        logger.info(
            f"Adding sticker via search: '{search_term}', selecting index {select_index}"
        )

        if not self.insta_actions.click_by_xpath(
            self.xpath_config.reel_edit_add_sticker_button, timeout=5
        ):
            logger.error("Failed to click 'Add Sticker' button.")
            return False
        time.sleep(1.5)

        if not self.insta_actions.wait_for_element_appear(
            self.xpath_config.reel_edit_sticker_asset_picker_container, timeout=5
        ):
            logger.error("Sticker tray did not appear.")
            return False

        if not self.insta_actions.input_text(
            self.xpath_config.reel_edit_sticker_search_bar_edittext,
            search_term,
            timeout=5,
        ):
            logger.error(f"Failed to type sticker search term: {search_term}")
            self.device.press("back")  # Try to close sticker tray
            return False
        time.sleep(2.5)  # Wait for search results

        # This XPath needs to correctly identify items in the search results.
        sticker_to_select_xpath = (
            self.xpath_config.reel_edit_sticker_list_item_by_index(select_index + 1)
        )  # XPath is 1-based
        if not self.insta_actions.click_by_xpath(sticker_to_select_xpath, timeout=7):
            logger.error(
                f"Failed to select sticker at index {select_index} (XPath index {select_index+1}) for search '{search_term}'."
            )
            self.device.press("back")  # Try to close sticker tray
            return False

        logger.info(f"Selected sticker for search '{search_term}'.")
        time.sleep(2)  # Allow sticker to be placed.
        # Sticker placement/sizing is complex and would go here if needed. For now, it's just added.
        return True

    def apply_video_filter(self, effect_name: str) -> bool:
        """
        Applies a main video filter/effect.
        Args:
            effect_name (str): The name of the effect (e.g., "VHS", "Cinematic HD", or "No effect").
        Returns:
            bool: True if filter was applied successfully.
        """
        logger.info(f"Applying video filter/effect: {effect_name}")

        if not self.insta_actions.click_by_xpath(
            self.xpath_config.reel_edit_effects_button, timeout=5
        ):
            logger.error("Failed to click main 'Effects' button (for video filters).")
            return False
        time.sleep(1.5)

        if not self.insta_actions.wait_for_element_appear(
            self.xpath_config.reel_edit_effects_gridview, timeout=7
        ):
            logger.error("Video effects grid/tray did not appear.")
            if self.insta_actions.element_exists(
                self.xpath_config.reel_edit_effects_bottom_sheet_drag_handle
            ):
                self.device.xpath(
                    self.xpath_config.reel_edit_effects_bottom_sheet_drag_handle
                ).swipe("down", steps=30)
            else:
                self.device.press("back")  # Fallback
            return False

        if effect_name.lower() == "none" or not effect_name:
            target_effect_xpath = (
                self.xpath_config.reel_edit_effect_apply_no_effect_button
            )
        else:
            target_effect_xpath = (
                self.xpath_config.reel_edit_effect_apply_button_by_name(effect_name)
            )

        # GridViews can be tricky to scroll. This might need a more robust scroll-and-find.
        # For simplicity, using the horizontal scroll helper, but vertical might be needed.
        if not self._find_item_in_horizontal_scrollable(  # Adapt if grid scrolls vertically
            item_name=effect_name,
            scrollable_xpath=self.xpath_config.reel_edit_effects_gridview,
            item_xpath_template=target_effect_xpath,
            max_swipes=5,
        ):
            logger.warning(
                f"Video effect '{effect_name}' not found or click failed in grid."
            )
            # Close effects tray anyway
            if self.insta_actions.element_exists(
                self.xpath_config.reel_edit_effects_bottom_sheet_drag_handle
            ):
                self.device.xpath(
                    self.xpath_config.reel_edit_effects_bottom_sheet_drag_handle
                ).swipe("down", steps=30)
            else:
                self.device.press("back")  # Fallback
            time.sleep(0.5)
            return False

        logger.info(f"Successfully selected video effect: {effect_name}")
        time.sleep(1)  # Allow effect to apply

        # Close the effects menu by dragging the handle
        if self.insta_actions.element_exists(
            self.xpath_config.reel_edit_effects_bottom_sheet_drag_handle
        ):
            self.device.xpath(
                self.xpath_config.reel_edit_effects_bottom_sheet_drag_handle
            ).swipe(
                "down", steps=40
            )  # More vigorous swipe
            logger.info("Closed video effects tray by dragging handle.")
        else:
            logger.warning(
                "Could not find drag handle to close video effects tray, trying device back button."
            )
            self.device.press("back")
        time.sleep(1)
        return True

    def tag_people(self, users_to_tag: List[str]) -> bool:
        """
        Tags specified users in the reel.
        Args:
            users_to_tag (List[str]): A list of usernames to tag.
        Returns:
            bool: True if tagging was successful.
        """
        if not users_to_tag:
            logger.info("No users to tag.")
            return True

        logger.info(f"Tagging users: {users_to_tag}")

        if not self.insta_actions.click_by_xpath(
            self.xpath_config.reel_edit_tag_people_button, timeout=5
        ):
            logger.error("Failed to click 'Tag people' button on edit screen.")
            return False
        time.sleep(1.5)  # Wait for tag screen

        # It's common to tap on the reel preview area first before 'Add Tag' becomes active or relevant
        # For simplicity, we'll try to click 'Add Tag' directly. If that fails, this tap might be needed.
        # self.device.click(self.device.info['displayWidth'] // 2, self.device.info['displayHeight'] // 2)
        # time.sleep(1)

        if not self.insta_actions.click_by_xpath(
            self.xpath_config.reel_tag_people_add_tag_button, timeout=7
        ):
            logger.error("Failed to click 'Add Tag' button on tag people screen.")
            self.device.press("back")
            return False
        time.sleep(1)

        for username in users_to_tag:
            logger.info(f"Searching for user to tag: {username}")
            if not self.insta_actions.input_text(
                self.xpath_config.reel_tag_people_search_bar_edittext,
                username,
                timeout=5,
                clear_first=True,
            ):
                logger.error(f"Failed to type username '{username}' in tag search bar.")
                continue
            time.sleep(3)  # Increased wait for search results

            user_result_xpath = self.xpath_config.reel_tag_people_search_result_user_container_by_username(
                username
            )
            if not self.insta_actions.click_by_xpath(user_result_xpath, timeout=5):
                logger.warning(
                    f"Could not find or click exact user '{username}'. Trying first available result."
                )
                first_result_xpath = self.xpath_config.reel_tag_people_search_result_user_container_by_index(
                    1
                )  # XPath index 1
                if not self.insta_actions.click_by_xpath(first_result_xpath, timeout=3):
                    logger.error(
                        f"Failed to click first user in search results for '{username}'. Skipping this user."
                    )
                    # Clear search for next user attempt
                    self.insta_actions.input_text(
                        self.xpath_config.reel_tag_people_search_bar_edittext,
                        " ",
                        timeout=2,
                        clear_first=True,
                    )
                    self.device.xpath(
                        self.xpath_config.reel_tag_people_search_bar_edittext
                    ).click()  # Refocus
                    time.sleep(0.5)
                    self.device.press("back")  # Close keyboard if it obscures things
                    time.sleep(0.5)
                    continue
                else:
                    logger.info(
                        f"Clicked first user in search results as fallback for '{username}'."
                    )
            else:
                logger.info(f"Successfully selected user '{username}' for tagging.")
            time.sleep(1.5)  # Wait for tag to be applied

            # Check if we need to click "Add Tag" again for the next user
            # This depends on the app's behavior after selecting a user for tagging
            if (
                users_to_tag.index(username) < len(users_to_tag) - 1
            ):  # If not the last user
                if not self.insta_actions.element_exists(
                    self.xpath_config.reel_tag_people_search_bar_edittext
                ):
                    # If search bar is gone, likely need to click "Add Tag" again
                    if not self.insta_actions.click_by_xpath(
                        self.xpath_config.reel_tag_people_add_tag_button, timeout=3
                    ):
                        logger.warning(
                            "Could not click 'Add Tag' for subsequent user. Stopping tagging for remaining users."
                        )
                        break
                    time.sleep(1)

        if not self.insta_actions.click_by_xpath(
            self.xpath_config.reel_tag_people_done_button, timeout=5
        ):
            logger.error(
                "Failed to click 'Done' button after attempting to tag people."
            )
            self.device.press("back")
            return False

        logger.info("Tagging process completed and 'Done' clicked.")
        time.sleep(1.5)  # Wait to return to main edit screen
        return True

    def proceed_to_share_page(self) -> bool:
        """
        Clicks the main 'Next' button on the reel editing page to navigate
        to the final share/caption screen.
        """
        logger.info("Proceeding to share/caption screen...")
        if not self.insta_actions.click_by_xpath(
            self.xpath_config.reel_edit_page_next_button, timeout=10
        ):
            logger.error(
                "Failed to click the main 'Next' button on the reel editing page."
            )
            return False

        if not self.insta_actions.wait_for_element_appear(
            self.xpath_config.reel_caption_text_view, timeout=15
        ):
            logger.error("Caption screen did not appear after clicking 'Next'.")
            # Try pressing back if stuck
            self.device.press("back")
            return False

        logger.info("Successfully navigated to the caption/share screen.")
        return True


# --- Orchestrator and Main Test Function ---


def orchestrate_reel_edits(
    device: u2.Device, insta_actions: InstagramInteractions, edit_steps: List[Dict]
) -> Tuple[bool, str]:
    """
    Orchestrates a series of reel edits based on a list of steps.
    Each step defines an action and its parameters.
    """
    editor = ReelEditor(device, insta_actions)

    for i, step in enumerate(edit_steps):
        action = step.get("action")
        params = step.get("params", {})
        logger.info(
            f"Executing edit step {i+1}/{len(edit_steps)}: {action} with params: {params}"
        )

        success = False
        if action == "add_text":
            success = editor.add_text(params)
        elif action == "add_sticker_search":
            success = editor.add_sticker_via_search(
                search_term=params.get("search_term"),
                select_index=params.get("select_index", 0),
            )
        elif action == "apply_video_filter":
            success = editor.apply_video_filter(params.get("name"))
        elif action == "tag_people":
            success = editor.tag_people(params.get("users_to_tag", []))
        # Add more actions here:
        # elif action == "add_audio":
        #     success = editor.add_audio(...) # You'd need to implement this
        else:
            logger.warning(f"Unknown edit action: {action}")
            continue  # Skip unknown action

        if not success:
            return False, f"Failed at edit step {i+1}: {action}"

        time.sleep(1)  # Small pause between distinct actions

    # After all individual edits, proceed to the share page
    if not editor.proceed_to_share_page():
        return False, "Failed to proceed to share page after edits."

    return True, "All reel edits applied successfully and navigated to share page."


def main_test_flexible_reel_editor():
    logger.info("--- Starting Flexible ReelEditor Test ---")

    DEVICE_ID = "R5CR7027Y7W"
    APP_PACKAGE_NAME = "com.instagram.androie"  # Or your actual package name

    # Define the sequence of edits and their parameters
    # For this test, we will ONLY do text edits as requested.
    test_edit_steps = [
        {
            "action": "add_text",
            "params": {
                "content": "Flexible Editor Test!",
                "font": "Typewriter",  # Make sure 'Typewriter' text is an option
                "color": "Red",  # Make sure 'Red color' is an option
                "animation": "Typewriter",  # 'Typewriter text animation style'
                "background_effect": "Sparkle",  # 'Sparkle text effect style'
                "alignment": "center",
            },
        },
        # { # Example of how you could add more steps for a fuller test
        #     "action": "add_text",
        #     "params": {
        #         "content": "#Uiautomator2",
        #         "font": "Classic",
        #         "color": "Blue",
        #         "alignment": "left"
        #     }
        # },
        # {
        #     "action": "add_sticker_search",
        #     "params": { "search_term": "Testing", "select_index": 0 }
        # },
        # {
        #     "action": "apply_video_filter",
        #     "params": { "name": "VHS" } # Ensure 'Apply effect VHS' exists
        # },
        # {
        #     "action": "tag_people",
        #     "params": { "users_to_tag": ["instagram"] }
        # }
    ]

    device = None
    try:
        logger.info(f"Connecting to device: {DEVICE_ID or 'default'}")
        device = u2.connect(DEVICE_ID)
        logger.info(f"Device connected: {device.info.get('productName', 'N/A')}")
        # S21 Devive id R5CR7027Y7W

        device.screen_on()
        if not device.info.get("screenOn"):
            device.keyevent("power")
            time.sleep(1)
        device.unlock()
        time.sleep(1)

        current_app = device.app_current()
        if current_app.get("package") != APP_PACKAGE_NAME:
            logger.warning(
                f"Current app is {current_app.get('package')}, not {APP_PACKAGE_NAME}."
            )
            logger.warning(
                f"Test assumes you are ON THE IG REEL EDITING PAGE for {APP_PACKAGE_NAME}."
            )

        logger.info(
            "USER ACTION: Ensure Instagram is open and ON THE REEL EDITING PAGE."
        )
        logger.info("Pausing for 10 seconds for manual setup if needed...")
        time.sleep(10)

        insta_actions = InstagramInteractions(device, app_package=APP_PACKAGE_NAME)

        logger.info("Starting reel edit orchestration...")
        success, message = orchestrate_reel_edits(
            device, insta_actions, test_edit_steps
        )

        if success:
            logger.info(f"✅ Flexible ReelEditor Test Result: SUCCESS - {message}")
        else:
            logger.error(f"❌ Flexible ReelEditor Test Result: FAILED - {message}")

    except Exception as e:
        logger.error(f"💥 An error occurred during the test: {e}", exc_info=True)
    finally:
        logger.info("--- Flexible ReelEditor Test Finished ---")


if __name__ == "__main__":
    # Requirements:
    # 1. Device connected, uiautomator2 server running (`python -m uiautomator2 init`).
    # 2. Instagram app (clone specified by APP_PACKAGE_NAME) installed.
    # 3. **MANUALLY NAVIGATE to the Instagram Reel editing page** (after selecting video, before adding any elements).
    # 4. All XPaths in `InstagramXPaths` must be correct for your app version and UI.
    main_test_flexible_reel_editor()
