Notes for posting bot.
# a a What to implement.
# TODO: Flow

# Script start on the reel edting page.
# We click add text
# We type in the text
# We then click font
# We swipe left, extract font names, if no match we swipe, check again
# We then click on color, select color that has been passed in config
# We then add in text animations
# Then we add text effect
# Then click done
# Then click next

# Once on reels page, get the children of this
# //androidx.recyclerview.widget.RecyclerView[@resource-id="com.instagram.androie:id/creation_toolbar_recyclerview"]


# Then get all teh settings from within, as shown below
# //android.widget.LinearLayout[@content-desc="Add audio"]


# We will have to list out all the settings that are in each option.
# All the front settings in this path
# //android.widget.LinearLayout[@resource-id="com.instagram.androie:id/postcapture_text_tool_menu_button_group"]

# Font size, Font style(there is 14 in this clone)
# //android.view.View[@content-desc="Stroke width tool"]

# Font color, There is many options. Colors can be found as show below
# //android.view.View[@content-desc="Black color"]
#
# Text animations
# //android.widget.ImageView[@content-desc="Text animation"]

# Animations are in here, this can be scrolled, with left swipe
# //androidx.recyclerview.widget.RecyclerView[@resource-id="com.instagram.androie:id/text_tool_animation_picker_recycler_view"]

# Example of one of the text animation paths.
# //android.widget.Button[@content-desc="Typewriter text animation style"]

# Text Effect
# All the effects are in this recyclerview
# //androidx.recyclerview.widget.RecyclerView[@resource-id="com.instagram.androie:id/text_tool_effect_picker_recycler_view"]

# No text effect button
# //android.widget.Button[@content-desc="No text effect style"]

# Example of an option in text effects
# //android.widget.Button[@content-desc="Sparkle text effect style"]

# Text alignment
# //android.widget.ImageView[@content-desc="Text alignment center"]

# Stickers
# //android.widget.Button[@content-desc="Add sticker"]

# The stickers are inside this containter
# /android.widget.FrameLayout[@resource-id="com.instagram.androie:id/asset_picker_container"]
# //android.widget.LinearLayout[@resource-id="com.instagram.androie:id/asset_picker"]
# //android.widget.FrameLayout[@resource-id="com.instagram.androie:id/asset_items_container"]

# Drag handle
# //android.widget.ImageView[@resource-id="com.instagram.androie:id/drag_chevron"]

# Sticker search bar
# //android.widget.LinearLayout[@resource-id="com.instagram.androie:id/search_bar_container"]

# Most of the stickers are here these two paths
# //androidx.recyclerview.widget.RecyclerView[@resource-id="com.instagram.androie:id/list"]/android.widget.LinearLayout[2]
# //androidx.recyclerview.widget.RecyclerView[@resource-id="com.instagram.androie:id/list"]/android.widget.LinearLayout[3]
# There is always 5 of the above lists on the screen, without scrolling they are the index's we want.
# If not selecting from the first menu, it would be better to just hard code in the options and use the serach

# Effects
# //android.widget.Button[@content-desc="Effects"]

#  No effects button
# //android.widget.Button[@content-desc="Apply effect No effect"]

# Effects are in this
# //android.widget.GridView[@resource-id="com.instagram.androie:id/camera_effect_preview_video_recycler_view"]

# Example of one of the effects
# //android.widget.Button[@content-desc="Apply effect Cinematic 𝐇𝐃"]

# To close the menu, the prisim handle must be dragged or flicked down
# //android.widget.ImageView[@resource-id="com.instagram.androie:id/bottom_sheet_drag_handle_prism"]

# Hashtags button
# //androidx.recyclerview.widget.RecyclerView[@resource-id="com.instagram.androie:id/caption_add_on_recyclerview"]/android.widget.LinearLayout[1]
# Poll button
# //androidx.recyclerview.widget.RecyclerView[@resource-id="com.instagram.androie:id/caption_add_on_recyclerview"]/android.widget.LinearLayout[2]

# Tag people
# I will need to get the text from within this xpath
# //android.widget.LinearLayout[@resource-id="com.instagram.androie:id/content_view"]/android.widget.Button[1]
# //android.widget.TextView[@resource-id="com.instagram.androie:id/title" and @text="Tag people"]

# Add Tag button
# //android.widget.FrameLayout[@resource-id="com.instagram.androie:id/add_people_tag_button"]

# Search bar for tagging other accounts
# //android.widget.EditText[@content-desc="Search for a user"]

# Serach results are in this path
# //android.widget.ListView[@resource-id="android:id/list"]

# Then each entery is indexed
# (//android.widget.Button[@resource-id="com.instagram.androie:id/row_search_user_container"])[1]

# Then we have these nested LinearLayouts
# In each of these there is a text view. Pull the text for the username for searching
# The row search user info is the clickable
# (//android.widget.LinearLayout[@resource-id="com.instagram.androie:id/row_search_user_info_container"])[1]/android.widget.LinearLayout/android.widget.LinearLayout[1]
# //android.widget.TextView[@resource-id="com.instagram.androie:id/row_search_user_username" and @text="nameyourcaketoppers"]

# //android.widget.TextView[@resource-id="com.instagram.androie:id/row_search_user_fullname" and @text="Name Your Cake I Toppers I Bases | Sellos | Raspes"]
# (//android.widget.LinearLayout[@resource-id="com.instagram.androie:id/row_search_user_info_container"])[1]/android.widget.LinearLayout/android.widget.LinearLayout[2]

# Then click the done
# //android.widget.Button[@content-desc="Done"]

