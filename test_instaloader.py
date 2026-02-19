import instaloader

L = instaloader.Instaloader()

try:
    shortcode = "C8wCLtmNfjq"
    post = instaloader.Post.from_shortcode(L.context, shortcode)
    print("Caption:", post.caption[:300] if post.caption else "NO CAPTION")
    print("Thumbnail URL:", post.url[:80] if post.url else "NONE")
    print("Typename:", post.typename)
    print("Owner:", post.owner_username)
except Exception as e:
    print("FAILED:", e)
