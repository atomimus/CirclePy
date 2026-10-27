"""Pure payload helpers for the Member profile and space resources."""

from copy import deepcopy


def profile_payload(name, avatar, headline, time_zone, messaging_enabled,
                    visible_in_member_directory, make_my_email_public, profile_fields):
    member = {key: value for key, value in dict(name=name, avatar=avatar,
              headline=headline, time_zone=time_zone).items() if value is not None}
    preferences = {key: value for key, value in dict(messaging_enabled=messaging_enabled,
                   visible_in_member_directory=visible_in_member_directory,
                   make_my_email_public=make_my_email_public).items() if value is not None}
    if preferences:
        member['preferences'] = preferences
    if profile_fields is not None:
        fields = deepcopy(profile_fields)
        for field in fields:
            # Preserve record IDs and future fields; translate only this legacy alias.
            if 'choices' in field:
                if 'community_member_choices_attributes' in field:
                    raise ValueError('Use either choices or community_member_choices_attributes')
                field['community_member_choices_attributes'] = field.pop('choices')
        member['community_member_profile_fields_attributes'] = fields
    if not member:
        raise ValueError('At least one field must be provided.')
    return deepcopy({'community_member': member})


def search_payload(page, per_page, search_text, exclude_empty_name, order, status, filters, search_after):
    return deepcopy(dict(page=page, per_page=per_page, search_text=search_text,
                         exclude_empty_name=exclude_empty_name, order=order, status=status,
                         filters=filters if filters is not None else [],
                         search_after=search_after if search_after is not None else []))


def page_params(page=None, per_page=None, **options):
    return deepcopy({key: value for key, value in dict(page=page, per_page=per_page,
                     **options).items() if value is not None})


def notification_params(space_ids):
    if space_ids is None:
        return None
    if isinstance(space_ids, (list, tuple, set)):
        space_ids = ','.join(str(value) for value in space_ids)
    return {'space_ids': space_ids}


def search_word(word):
    if not word:
        raise ValueError('word must be a non-empty string')
    return str(word)


def filter_spaces(spaces, word, case_sensitive, include_slug):
    if isinstance(spaces, dict):
        # Error JSON must survive instead of looking like zero matches.
        # The documented /spaces success shape is a bare list.
        if 'records' not in spaces:
            return spaces
        spaces = spaces['records']
    if not isinstance(spaces, list) or any(not isinstance(item, dict) for item in spaces):
        raise ValueError('Expected a spaces list or an object with a records list')
    needle = word if case_sensitive else word.lower()
    results = []
    for space in spaces:
        values = [str(space.get('name', ''))]
        if include_slug:
            values.append(str(space.get('slug', '')))
        if any(needle in (value if case_sensitive else value.lower()) for value in values):
            results.append(space)
    return results
