# start dev server

```
uvicorn app.main:app --reload --port 8000
```

# cURL test commands

### CREATE ENTRY

```
curl -X POST http://localhost:8000/api/video-annotations \
         -H "Content-Type: application/json" \
         -d '{
        "video": { "video_id": "video1234", "gcs_uri": "gcs://this/is/a/uri" },
        "identified_product" : [{
                "title": "Cool lamp",
                "description": "item description",
                "color_pattern_style_usage" : "color_pattern_style_usage",
                "category" : "category1",
                "subcategory": "subcategory2",
                "image_timestamp_ms" : 1761749979123,
                "matched_product" : [{
                        "offer_id" : "matched_offer_id1",
                        "rank": 1
                },
                {
                        "offer_id" : "matched_offer_id2",
                        "rank": 2
                }]
        }]
}
'
```

### READ ENTRY

```
curl http://localhost:8000/api/video-annotations/[:id]
```

### READ ALL

```
curl http://localhost:8000/api/video-annotations
```

### UPDATE ENTRY

```
curl -X PUT http://localhost:8000/api/video-annotations/[:id] \
         -H "Content-Type: application/json" \
         -d '{
        "video": { "video_id": "video1234", "gcs_uri": "gcs://this/is/a/uri" },
        "identified_product" : [{
                "title": "Cool lamp",
                "description": "item description",
                "color_pattern_style_usage" : "color_pattern_style_usage",
                "category" : "category1",
                "subcategory": "subcategory2",
                "image_timestamp_ms" : 1761749979123,
                "matched_product" : [{
                        "offer_id" : "matched_offer_id1",
                        "rank": 1
                }]
        }]
      }'
```

### DELETE ENTRY

```
curl -X DELETE http://localhost:8000/api/video-annotations/[:id]
```

### ROW DATA SCHEMA IN JSON

```
{
  "id": "annotation-id-1234",
  "video": { "video_id": "video1234", "gcs_uri": "gcs://this/is/a/uri" },
  "identified_product" : [{
        "title": "Cool lamp",
        "description": "item description",
        "color_pattern_style_usage" : "color_pattern_style_usage",
        "category" : "category1",
        "subcategory": "subcategory2",
        "image_timestamp_ms" : 1761749979123,
        "matched_product" : [{
                "offer_id" : "matched_offer_id1",
                "rank": 1
        },
        {
                "offer_id" : "matched_offer_id2",
                "rank": 2
        }]
  }]
}
```
