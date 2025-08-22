"""IZ item processor service"""
from wrlc_alma_api_client.models import Item

from alma_item_checks_processor_service.services.base_processor import BaseItemProcessor
from alma_item_checks_processor_service.config import CHECKED_IZ_LOCATIONS


class IZItemProcessor(BaseItemProcessor):
    """IZ item processor service"""
    def should_process(self) -> list[str] | None:
        """Check if IZ item should be processed

        """
        should_process: list[str] = []

        if self.no_row_tray_should_process():
            should_process.append('iz_now_row_tray')

        return should_process

    def process(self, processes: list[str]) -> None:
        """Process IZ item

        Args:
            processes (list[str]): Processes to run
        """
        for process in processes:
            if process == "iz_no_row_tray":
                self.no_row_tray_process()

    def no_row_tray_should_process(self) -> bool:
        """Check if IZ no row tray data

        """
        item: Item = self.parsed_item.get('item_data')
        iz: str = self.parsed_item.get("institution_code")
        location_code: str | None = item.item_data.location.value
        temp_location_code: str | None = item.holding_data.temp_location.value

        if location_code not in CHECKED_IZ_LOCATIONS or temp_location_code not in CHECKED_IZ_LOCATIONS:
            return False

        if self.no_row_tray_data() or self.wrong_row_tray_data(iz):
            return True

        return False

    def no_row_tray_process(self) -> bool:
        """Process IZ no row tray data"""
        # TODO: Process IZ no row tray data items
