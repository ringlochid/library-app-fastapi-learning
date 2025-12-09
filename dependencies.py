from fastapi import Query, HTTPException, status
from typing import List
from schemas.book import BookSortControl, SortField, SortDirection


def parse_sort(
    sort: List[str] = Query(
        default=[], description="Sort spec like 'similarity:desc', 'title:asc'"
    )
) -> List[BookSortControl]:
    result: List[BookSortControl] = []

    for item in sort:
        try:
            field_str, dir_str = item.split(":", 1)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid sort item '{item}', expected 'field:direction'",
            )

        try:
            field = SortField(field_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid sort field '{field_str}'",
            )

        try:
            direction = SortDirection(dir_str.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid sort direction '{dir_str}'",
            )

        result.append(BookSortControl(sort_field=field, sort_direction=direction))

    return result
