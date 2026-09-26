import cloudinary.uploader
import time
from rest_framework import serializers
from rest_framework.exceptions import APIException

def upload_image(file, folder, private=False):
    field = serializers.ImageField()
    file = field.run_validation(file)
    if file.size > 10 * 1024 * 1024:
        raise serializers.ValidationError('Images must be at most 10 MB.')
    if file.image.format not in {'JPEG', 'PNG', 'WEBP'}:
        raise serializers.ValidationError('Only JPEG, PNG and WebP images are supported.')
    file.seek(0)
    try:
        result = cloudinary.uploader.upload(file, folder='batax/' + folder, resource_type='image',
                                            type='authenticated' if private else 'upload',
                                            **({'format': 'jpg'} if private else {}))
    except Exception as exc:
        raise APIException('Image storage is unavailable. Please retry.') from exc
    return result


def private_image_url(public_id):
    return cloudinary.utils.private_download_url(public_id, 'jpg', resource_type='image',
        type='authenticated', expires_at=int(time.time()) + 300, attachment=False)
