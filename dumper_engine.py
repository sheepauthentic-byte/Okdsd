# Language: Python 3.10+
# Target: Universal Deep Dumper & Regex Credential Extractor for Any Website

import os
import time
import re
import logging
from pathlib import Path
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from curl_cffi import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class UniversalDeepDumper:
    def __init__(self, target_url: str, status_callback=None):
        self.target_url = target_url.rstrip("/")
        self.status_callback = status_callback
        self.output_dir = Path("downloaded_resources")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.result_file = Path("acccheck.txt")
        
        parsed = urlparse(self.target_url)
        self.base_domain = f"{parsed.scheme}://{parsed.netloc}"
        
        # Session giả lập TLS fingerprint Chrome 120 (vượt WAF/Cloudflare mọi trang web)
        self.session = requests.Session(impersonate="chrome120")
        self.session.headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": self.base_domain,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        })
        self.collected_links = set()
        self.visited_pages = set()

    def log(self, message: str):
        logging.info(message)
        if self.status_callback:
            self.status_callback(message)

    def run(self, max_pages: int = 10):
        self.log(f"[*] Bắt đầu quét sâu toàn diện mục tiêu: {self.target_url}")
        
        # Bước 1: Quét trang chủ và dò tìm phân trang thông minh đa luồng
        self._deep_crawl_index()

        with ThreadPoolExecutor(max_workers=10) as executor:
            list(executor.map(self._scrape_pagination, range(1, max_pages + 1)))

        if not self.collected_links:
            self.log("[-] Không tìm thấy liên kết tài nguyên nào trên website này.")
            return

        self.log(f"[+] Tìm thấy tổng cộng {len(self.collected_links)} liên kết file. Bắt đầu tải xuống song song...")
        
        # Bước 2: Tải xuống đa luồng các tài nguyên
        with ThreadPoolExecutor(max_workers=10) as executor:
            list(executor.map(self._download_file, self.collected_links))

        # Bước 3: Trích xuất user:pass bằng Regex chuyên sâu vào acccheck.txt
        self._extract_credentials()

    def _deep_crawl_index(self):
        try:
            res = self.session.get(self.target_url, timeout=15)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                for tag in soup.find_all(['a', 'link', 'script'], href=True):
                    href = tag.get('href') or tag.get('src')
                    if href:
                        full_url = urljoin(self.base_domain, href)
                        if any(ext in href.lower() for ext in ['.txt', '.zip', '.rar', '.csv', '.json', '/download/', '/file/', '/api/']):
                            self.collected_links.add(full_url)
        except Exception as e:
            self.log(f"[-] Lỗi quét trang chủ: {str(e)}")

    def _scrape_pagination(self, page: int):
        # Các mẫu đường dẫn phân trang phổ biến trên hầu hết các nền tảng web
        dynamic_paths = [
            f"{self.target_url}/products?page={page}",
            f"{self.target_url}/shop?page={page}",
            f"{self.target_url}/category?page={page}",
            f"{self.target_url}/search?page={page}",
            f"{self.target_url}/page/{page}",
            f"{self.target_url}/?p={page}"
        ]
        
        for url in dynamic_paths:
            if url in self.visited_pages:
                continue
            self.visited_pages.add(url)
            try:
                res = self.session.get(url, timeout=10)
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, 'html.parser')
                    for tag in soup.find_all(['a', 'link'], href=True):
                        href = tag['href']
                        if any(ext in href.lower() for ext in ['.txt', '.zip', '.rar', '.csv', '.json', '/download/', '/file/']):
                            self.collected_links.add(urljoin(self.base_domain, href))
            except Exception:
                continue
            time.sleep(0.2)

    def _download_file(self, file_url: str):
        try:
            parsed_path = urlparse(file_url).path
            filename = os.path.basename(parsed_path) or f"res_{int(time.time())}.txt"
            save_path = self.output_dir / filename
            if save_path.exists():
                return
            
            r = self.session.get(file_url, stream=True, timeout=20)
            if r.status_code == 200:
                with open(save_path, 'wb') as f:
                    for chunk in r.iter_content(8192):
                        if chunk:
                            f.write(chunk)
                self.log(f"[+] Tải thành công: {filename}")
        except Exception:
            pass

    def _extract_credentials(self):
        self.log("[*] Đang phân tích nội dung file và trích xuất dữ liệu user:pass (combolist)...")
        extracted_credentials = set()
        
        # Biểu thức chính quy quét định dạng email:password hoặc user:password tiêu chuẩn
        credential_pattern = re.compile(r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+:[^\s]+|[a-zA-Z0-9_]{3,30}:[^\s]+)')

        for file_path in self.output_dir.glob("*.*"):
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                matches = credential_pattern.findall(content)
                for match in matches:
                    extracted_credentials.add(match)
            except Exception:
                pass

        with open(self.result_file, "w", encoding="utf-8") as outfile:
            for cred in sorted(extracted_credentials):
                outfile.write(cred + "\n")

        self.log(f"[+] HOÀN TẤT: Trích xuất thành công {len(extracted_credentials)} tài khoản sạch vào {self.result_file.name}")
