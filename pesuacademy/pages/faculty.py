from bs4 import BeautifulSoup
import requests_html
from typing import Optional
from pesuacademy.models.professor import Professor


class FacultyPageHandler:
    departments = {
        "arch": "architecture",
        "bt": "biotechnology",
        "cv": "civil",
        "cse": "computer-science",
        "cse-aiml": "computer-science-AIML",
        "ca": "computer-application",
        "des": "design",
        "eee": "electrical-&-electronics",
        "ece": "electronics-&-communications",
        "law": "law",
        "me": "mechanical",
        "ms": "management-studies",
        "sh": "science-&-humanities",
        "com": "commerce",
        "psy": "psychology",
        "cie": "centre-for-innovation-&-entrepreneurship",
        "ps": "pharmaceutical-sciences",
    }
    campuses = ["rr", "ec", "hn"]

    @staticmethod
    def get_urls_from_campus_and_department(
        campus: Optional[str], department: Optional[str]
    ):
        base_url = "https://staff.pes.edu/{campus}/atoz/{department}"
        if department:
            assert (
                department in FacultyPageHandler.departments
            ), "Invalid department provided."
        if campus:
            assert campus in FacultyPageHandler.campuses, "Invalid campus provided."

        if not department and not campus:
            urls = [base_url.format(campus="", department="")]
        elif department and not campus:
            urls = [
                base_url.format(
                    campus=campus, department=FacultyPageHandler.departments[department]
                )
                for campus in ["rr", "ec", "hn"]
            ]
        elif campus and not department:
            urls = [
                base_url.format(
                    campus=campus, department=FacultyPageHandler.departments[department]
                )
                for department in FacultyPageHandler.departments
            ]
        else:
            urls = [
                base_url.format(
                    campus=campus, department=FacultyPageHandler.departments[department]
                )
            ]
        return urls

    @staticmethod
    def get_all_faculty_ids_from_url(
        session: requests_html.HTMLSession, url: str, page: int = 1
    ) -> list[str]:
        try:
            current_url = f"{url}?page={page}"
            print("entered loop", page, current_url)
            response = session.get(current_url)
            if response.status_code != 200:
                return []
            else:
                soup = BeautifulSoup(response.text, "html.parser")
                if next_page := soup.find("a", class_="nextposts-link"):
                    next_page_number = int(next_page["href"].split("?page=")[-1])
                else:
                    next_page_number = None

                print("Next page number", next_page_number)
                faculty_divs = soup.find_all("div", class_="staff-profile")
                faculty_ids = [
                    div.find("a", class_="geodir-category-img_item")["href"].split("/")[
                        -2
                    ]
                    for div in faculty_divs
                ]
                if next_page_number is not None:
                    faculty_ids.extend(
                        FacultyPageHandler.get_all_faculty_ids_from_url(
                            session, url, next_page_number
                        )
                    )
                return faculty_ids
            
        except Exception:
            return []

    @staticmethod
    def get_faculty_by_id(
        session: requests_html.HTMLSession, faculty_id: str
    ) -> Professor:
        url = f"https://staff.pes.edu/{faculty_id}"
        # print(url)
        response = session.get(url)
        if response.status_code != 200:
            raise ConnectionError(f"Failed to fetch URL: {url}")

        soup = BeautifulSoup(response.text, "html.parser")
        name = soup.find("h4").text.strip()
        domains = [
            item.text.strip()
            for item in soup.select(
                "#tab-teaching .bookings-item-content ul.ul-item-left li"
            )
        ]
        designation = soup.find("h5").text.strip()
        designation = [d.strip() for d in designation.split(",")]
        # print()
         # Education
        professor_education = []
        education_section = soup.find_all("h3")
        education_section_filter = [
            h3 for h3 in education_section if h3.get_text(strip=True) == "Education"
        ]

        for h3 in education_section_filter:
            education_list = h3.find_next("ul", class_="ul-item-left")
            if education_list:
                education_items = education_list.find_all("li")
                education_details = [
                    item.find("p").text.strip() for item in education_items
                ]
                for detail in education_details:
                    professor_education.append(detail)

        # print(professor_education)

        # Experience
        professor_experience = []
        experience_section = soup.find_all("h3")
        experience_section_filter = [
            h3 for h3 in experience_section if h3.get_text(strip=True) == "Experience"
        ]
        for h3 in experience_section_filter:
            experience_list = h3.find_next("ul", class_="ul-item-left")
            if experience_list:
                experience_items = experience_list.find_all("li")
                experience_details = [
                    item.find("p").text.strip() for item in experience_items
                ]
                for detail in experience_details:
                    professor_experience.append(detail)

        # print(professor_experience)

        # email
        all_a_tags = soup.find_all("a")
        email = [
            tag
            for tag in all_a_tags
            if "pes.edu" in tag.get("href", "") and "pes.edu" in tag.get_text()
        ]
        if email:
            email = email[0].get_text()
        # department
        department_element = soup.find("li", class_="contat-card")
        department_paragraph = department_element.find("p")
        department = department_paragraph.get_text(strip=True)
        # campus
        try:
            campus_element = soup.find_all("li", class_="contat-card")[1]
            if campus_element:
                campus_paragraph = campus_element.find("p")
                campus = campus_paragraph.get_text(strip=True)
        except IndexError:
            campus = None
        # responsibilities
        responsibilities = []
        responsibilities_div = soup.find("div", id="tab-responsibilities")
        if responsibilities_div is not None:
            p_tags = responsibilities_div.find_all("p")
            responsibilities = [p.text for p in p_tags]
        
        Pesu_Staff = Professor(
            name=name,
            designation=designation,
            education=professor_education,
            experience=professor_experience,
            department=department,
            campus=campus,
            domains=domains,
            email=email,
            responsibilities=responsibilities,
        )
        return Pesu_Staff
    
    def get_faculty_by_name(self, name: str, session: requests_html.HTMLSession) -> list[Professor]:
        professors: list[Professor] = []
        url = f"https://staff.pes.edu/atoz/list/?search={name}"
        response = session.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        faculty_divs = soup.find_all("div", class_="col-md-3 left-padding-0")

        faculty_ids = [
            div.find("a", class_="chat-contacts-item")["href"].split("/")[-2]
            for div in faculty_divs
        ]
        print(faculty_ids)
        # Retrieve details for each faculty ID
        for faculty_id in faculty_ids:
            professor = self.get_faculty_by_id(session, faculty_id)
            if professor:
                professors.append(professor)

        return professors

        

    def get_page(
        self,
        session: requests_html.HTMLSession,
        campus: Optional[str] = None,
        department: Optional[str] = None,
        designation: Optional[str] = None,
        name:Optional[str] = None
    ) -> list[Professor]:
        urls = self.get_urls_from_campus_and_department(campus, department)
        # TODO: Add search functionality for name: https://staff.pes.edu/atoz/list/?search={name}
        if name:
            professors=self.get_faculty_by_name(name,session)
            return professors
        print(urls)
        professors: list[Professor] = list()
        for url in urls:
            faculty_ids = self.get_all_faculty_ids_from_url(session, url, page=1)
            for faculty_id in faculty_ids:
                professor = self.get_faculty_by_id(session, faculty_id)
                # print(professor.designation)
                if designation is None or designation in professor.designation:
                    professors.append(professor)
        return professors


