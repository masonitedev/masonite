"""Cache Config"""

STORES = {
    "default": "local",
    "local": {
        "driver": "file",
        "location": "local/storage/framework/cache"
    },
}
