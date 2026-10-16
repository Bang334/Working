"""Font management service for dynamic global typography."""

import json
import os
from pathlib import Path
from typing import Any, Dict, List

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FONT_SETTINGS_FILE = DATA_DIR / "font_settings.json"

# Danh sách 100 Google Fonts tuyển chọn kỹ càng: Hỗ trợ tiếng Việt đầy đủ và kết hợp CJK
FONT_COLLECTION: List[Dict[str, Any]] = [
    # ==========================================
    # NHÓM 1: SERIF & SANG TRỌNG (20 fonts)
    # ==========================================
    {
        "id": "merriweather",
        "name": "Merriweather",
        "family": "'Merriweather', 'Microsoft JhengHei', '微軟正黑體', serif",
        "category": "serif",
        "category_label": "Thanh Lịch & Sang Trọng",
        "desc": "Nét chữ serif trang nhã, ấm cúng, cực kỳ êm mắt trên màn hình (Khuyên dùng)",
        "weights": "300,400,700,900",
        "is_default": True
    },
    {
        "id": "playfair-display",
        "name": "Playfair Display",
        "family": "'Playfair Display', 'Microsoft JhengHei', '微軟正黑體', serif",
        "category": "serif",
        "category_label": "Thanh Lịch & Sang Trọng",
        "desc": "Tương phản nét thanh nét đậm cổ điển, chuẩn ấn phẩm tạp chí thượng lưu",
        "weights": "400,600,700,900"
    },
    {
        "id": "lora",
        "name": "Lora",
        "family": "'Lora', 'Microsoft JhengHei', '微軟正黑體', serif",
        "category": "serif",
        "category_label": "Thanh Lịch & Sang Trọng",
        "desc": "Đường cong mượt mà, cảm giác thư thái của tiểu thuyết văn học",
        "weights": "400,500,600,700"
    },
    {
        "id": "cormorant-garamond",
        "name": "Cormorant Garamond",
        "family": "'Cormorant Garamond', 'Microsoft JhengHei', '微軟正黑體', serif",
        "category": "serif",
        "category_label": "Thanh Lịch & Sang Trọng",
        "desc": "Kế thừa trường phái Garamond quý tộc thế kỷ 16 thanh tao",
        "weights": "300,400,600,700"
    },
    {
        "id": "eb-garamond",
        "name": "EB Garamond",
        "family": "'EB Garamond', 'Microsoft JhengHei', '微軟正黑體', serif",
        "category": "serif",
        "category_label": "Thanh Lịch & Sang Trọng",
        "desc": "Cổ điển chuẩn mực Châu Âu, hoàn hảo cho tiêu đề hợp đồng danh giá",
        "weights": "400,500,600,700,800"
    },
    {
        "id": "cinzel",
        "name": "Cinzel",
        "family": "'Cinzel', 'Microsoft JhengHei', '微軟正黑體', serif",
        "category": "serif",
        "category_label": "Thanh Lịch & Sang Trọng",
        "desc": "Khắc bia đá La Mã cổ đại, uy nghiêm và trường tồn",
        "weights": "400,600,700,800"
    },
    {
        "id": "crimson-pro",
        "name": "Crimson Pro",
        "family": "'Crimson Pro', 'Microsoft JhengHei', '微軟正黑體', serif",
        "category": "serif",
        "category_label": "Thanh Lịch & Sang Trọng",
        "desc": "Font sách học thuật kinh điển, chân phương và đĩnh đạc",
        "weights": "300,400,600,700"
    },
    {
        "id": "bitter",
        "name": "Bitter",
        "family": "'Bitter', 'Microsoft JhengHei', '微軟正黑體', serif",
        "category": "serif",
        "category_label": "Thanh Lịch & Sang Trọng",
        "desc": "Serif dày dặn chắc khỏe (Slab Serif), dễ đọc ở mọi độ phân giải",
        "weights": "400,500,600,700"
    },
    {
        "id": "bodoni-moda",
        "name": "Bodoni Moda",
        "family": "'Bodoni Moda', 'Microsoft JhengHei', '微軟正黑體', serif",
        "category": "serif",
        "category_label": "Thanh Lịch & Sang Trọng",
        "desc": "Thời thượng như bìa Vogue & ELLE, độ tương phản sắc sảo",
        "weights": "400,600,700,900"
    },
    {
        "id": "prata",
        "name": "Prata",
        "family": "'Prata', 'Microsoft JhengHei', '微軟正黑體', serif",
        "category": "serif",
        "category_label": "Thanh Lịch & Sang Trọng",
        "desc": "Giọt nước thanh tú và đường lượn chữ hình học mềm mại",
        "weights": "400"
    },
    {
        "id": "spectral",
        "name": "Spectral",
        "family": "'Spectral', 'Microsoft JhengHei', '微軟正黑體', serif",
        "category": "serif",
        "category_label": "Thanh Lịch & Sang Trọng",
        "desc": "Thiết kế riêng cho các ứng dụng web hiển thị tài liệu dày đặc",
        "weights": "300,400,500,600,700"
    },
    {
        "id": "libre-baskerville",
        "name": "Libre Baskerville",
        "family": "'Libre Baskerville', 'Microsoft JhengHei', '微軟正黑體', serif",
        "category": "serif",
        "category_label": "Thanh Lịch & Sang Trọng",
        "desc": "Baskerville hiện đại hóa, khoảng cách thoáng đãng, dễ đọc",
        "weights": "400,700"
    },
    {
        "id": "frank-ruhl-libre",
        "name": "Frank Ruhl Libre",
        "family": "'Frank Ruhl Libre', 'Microsoft JhengHei', '微軟正黑體', serif",
        "category": "serif",
        "category_label": "Thanh Lịch & Sang Trọng",
        "desc": "Nét chữ cổ kính, đĩnh đạc mang phong vị thủ công",
        "weights": "300,400,500,700"
    },
    {
        "id": "newsreader",
        "name": "Newsreader",
        "family": "'Newsreader', 'Microsoft JhengHei', '微軟正黑體', serif",
        "category": "serif",
        "category_label": "Thanh Lịch & Sang Trọng",
        "desc": "Font báo chí kinh viện, tạo sự tin cậy tuyệt đối cho báo giá",
        "weights": "400,500,600,700"
    },
    {
        "id": "faustina",
        "name": "Faustina",
        "family": "'Faustina', 'Microsoft JhengHei', '微軟正黑體', serif",
        "category": "serif",
        "category_label": "Thanh Lịch & Sang Trọng",
        "desc": "Gọn gàng, tiết kiệm không gian ngang nhưng vẫn giữ trọn nét đài các",
        "weights": "400,500,600,700"
    },
    {
        "id": "besley",
        "name": "Besley",
        "family": "'Besley', 'Microsoft JhengHei', '微軟正黑體', serif",
        "category": "serif",
        "category_label": "Thanh Lịch & Sang Trọng",
        "desc": "Dựa trên Clarendon nổi tiếng, chân chữ bám đáy vững vàng",
        "weights": "400,500,600,700"
    },
    {
        "id": "petrona",
        "name": "Petrona",
        "family": "'Petrona', 'Microsoft JhengHei', '微軟正黑體', serif",
        "category": "serif",
        "category_label": "Thanh Lịch & Sang Trọng",
        "desc": "Nét móc mềm, chân đế cách điệu uyển chuyển",
        "weights": "300,400,500,600,700"
    },
    {
        "id": "castoro",
        "name": "Castoro",
        "family": "'Castoro', 'Microsoft JhengHei', '微軟正黑體', serif",
        "category": "serif",
        "category_label": "Thanh Lịch & Sang Trọng",
        "desc": "Phong cách học thuật Ý cổ, sắc nét đến từng đường viền",
        "weights": "400"
    },
    {
        "id": "vollkorn",
        "name": "Vollkorn",
        "family": "'Vollkorn', 'Microsoft JhengHei', '微軟正黑體', serif",
        "category": "serif",
        "category_label": "Thanh Lịch & Sang Trọng",
        "desc": "Chân chữ dày nảy nở, tạo cảm giác thân mật và chân thành",
        "weights": "400,600,700"
    },
    {
        "id": "alegreya",
        "name": "Alegreya",
        "family": "'Alegreya', 'Microsoft JhengHei', '微軟正黑體', serif",
        "category": "serif",
        "category_label": "Thanh Lịch & Sang Trọng",
        "desc": "Nhịp điệu văn thơ êm ái, một trong 53 font đẹp nhất thập kỷ",
        "weights": "400,500,600,700"
    },

    # ==========================================
    # NHÓM 2: BO TRÒN & THÂN THIỆN (18 fonts)
    # ==========================================
    {
        "id": "quicksand",
        "name": "Quicksand",
        "family": "'Quicksand', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "rounded",
        "category_label": "Bo Tròn & Mềm Mại",
        "desc": "Hình học bo tròn hoàn hảo, trẻ trung, hiện đại và rất dễ thương",
        "weights": "400,500,600,700"
    },
    {
        "id": "nunito",
        "name": "Nunito",
        "family": "'Nunito', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "rounded",
        "category_label": "Bo Tròn & Mềm Mại",
        "desc": "Đường nét bo tròn cân đối, chuẩn mực giao diện ứng dụng quốc tế",
        "weights": "400,500,600,700,800"
    },
    {
        "id": "comfortaa",
        "name": "Comfortaa",
        "family": "'Comfortaa', 'Microsoft JhengHei', '微軟正黑體', cursive",
        "category": "rounded",
        "category_label": "Bo Tròn & Mềm Mại",
        "desc": "Vòng tròn nguyên bản tối giản, êm ái tựa như công nghệ thân thiện",
        "weights": "400,500,600,700"
    },
    {
        "id": "baloo-2",
        "name": "Baloo 2",
        "family": "'Baloo 2', 'Microsoft JhengHei', '微軟正黑體', cursive",
        "category": "rounded",
        "category_label": "Bo Tròn & Mềm Mại",
        "desc": "Mũm mĩm, căng tràn sức sống, rất thu hút mắt nhìn",
        "weights": "400,500,600,700,800"
    },
    {
        "id": "fredoka",
        "name": "Fredoka",
        "family": "'Fredoka', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "rounded",
        "category_label": "Bo Tròn & Mềm Mại",
        "desc": "Nét bo tròn đậm đà, cực kỳ tươi sáng và năng động",
        "weights": "400,500,600,700"
    },
    {
        "id": "varela-round",
        "name": "Varela Round",
        "family": "'Varela Round', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "rounded",
        "category_label": "Bo Tròn & Mềm Mại",
        "desc": "Gọn gàng, thanh thoát, thích hợp cả cho tiêu đề lẫn văn bản",
        "weights": "400"
    },
    {
        "id": "dosis",
        "name": "Dosis",
        "family": "'Dosis', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "rounded",
        "category_label": "Bo Tròn & Mềm Mại",
        "desc": "Thân chữ cao thon thả (Condensed) kết hợp đầu bo tròn tinh tế",
        "weights": "400,500,600,700"
    },
    {
        "id": "asap",
        "name": "Asap",
        "family": "'Asap', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "rounded",
        "category_label": "Bo Tròn & Mềm Mại",
        "desc": "Góc bo nhẹ nhàng, giữ cùng độ rộng trên mọi weight",
        "weights": "400,500,600,700"
    },
    {
        "id": "signika-negative",
        "name": "Signika Negative",
        "family": "'Signika Negative', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "rounded",
        "category_label": "Bo Tròn & Mềm Mại",
        "desc": "Thiết kế cho hệ thống biển báo, rõ nét từ khoảng cách xa",
        "weights": "400,500,600,700"
    },
    {
        "id": "sniglet",
        "name": "Sniglet",
        "family": "'Sniglet', 'Microsoft JhengHei', '微軟正黑體', cursive",
        "category": "rounded",
        "category_label": "Bo Tròn & Mềm Mại",
        "desc": "Cong tròn ngộ nghĩnh, tạo cảm giác vô cùng gần gũi",
        "weights": "400,800"
    },
    {
        "id": "mali",
        "name": "Mali",
        "family": "'Mali', 'Microsoft JhengHei', '微軟正黑體', cursive",
        "category": "rounded",
        "category_label": "Bo Tròn & Mềm Mại",
        "desc": "Viết tay học trò ngây thơ, thoải mái và phóng khoáng",
        "weights": "400,500,600,700"
    },
    {
        "id": "itim",
        "name": "Itim",
        "family": "'Itim', 'Microsoft JhengHei', '微軟正黑體', cursive",
        "category": "rounded",
        "category_label": "Bo Tròn & Mềm Mại",
        "desc": "Viết tay đơn giản, mộc mạc và chân thật",
        "weights": "400"
    },
    {
        "id": "sriracha",
        "name": "Sriracha",
        "family": "'Sriracha', 'Microsoft JhengHei', '微軟正黑體', cursive",
        "category": "rounded",
        "category_label": "Bo Tròn & Mềm Mại",
        "desc": "Nét bút lông đầu tù, ấm áp và đậm nét Á Đông",
        "weights": "400"
    },
    {
        "id": "concert-one",
        "name": "Concert One",
        "family": "'Concert One', 'Microsoft JhengHei', '微軟正黑體', cursive",
        "category": "rounded",
        "category_label": "Bo Tròn & Mềm Mại",
        "desc": "Đường nét bo tròn lấy cảm hứng từ áp phích âm nhạc thập niên 50",
        "weights": "400"
    },
    {
        "id": "lexend",
        "name": "Lexend",
        "family": "'Lexend', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "rounded",
        "category_label": "Bo Tròn & Mềm Mại",
        "desc": "Tối ưu hóa khả năng đọc nhanh theo nghiên cứu giáo dục",
        "weights": "400,500,600,700"
    },
    {
        "id": "chivo",
        "name": "Chivo",
        "family": "'Chivo', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "rounded",
        "category_label": "Bo Tròn & Mềm Mại",
        "desc": "Grotesque thanh lịch với góc bo mềm mại ở các điểm nối",
        "weights": "400,500,600,700"
    },
    {
        "id": "be-vietnam-pro",
        "name": "Be Vietnam Pro",
        "family": "'Be Vietnam Pro', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "rounded",
        "category_label": "Bo Tròn & Mềm Mại",
        "desc": "Font thiết kế riêng cho người Việt, dấu thanh chuẩn mực hoàn mỹ",
        "weights": "400,500,600,700"
    },
    {
        "id": "patrick-hand",
        "name": "Patrick Hand",
        "family": "'Patrick Hand', 'Microsoft JhengHei', '微軟正黑體', cursive",
        "category": "rounded",
        "category_label": "Bo Tròn & Mềm Mại",
        "desc": "Bút máy viết tay tự nhiên của tác giả, gọn gàng và dễ mến",
        "weights": "400"
    },

    # ==========================================
    # NHÓM 3: HIỆN ĐẠI & TINH TẾ (20 fonts)
    # ==========================================
    {
        "id": "inter",
        "name": "Inter",
        "family": "'Inter', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "modern",
        "category_label": "Hiện Đại & Tinh Tế",
        "desc": "Font giao diện công nghệ số 1 thế giới, sắc sảo từng pixel",
        "weights": "400,500,600,700,800"
    },
    {
        "id": "montserrat",
        "name": "Montserrat",
        "family": "'Montserrat', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "modern",
        "category_label": "Hiện Đại & Tinh Tế",
        "desc": "Lấy cảm hứng từ biển hiệu phố cổ Buenos Aires, mạnh mẽ và tự tin",
        "weights": "400,500,600,700,800"
    },
    {
        "id": "plus-jakarta-sans",
        "name": "Plus Jakarta Sans",
        "family": "'Plus Jakarta Sans', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "modern",
        "category_label": "Hiện Đại & Tinh Tế",
        "desc": "Đang là xu hướng thiết kế SaaS cao cấp hàng đầu hiện nay",
        "weights": "400,500,600,700,800"
    },
    {
        "id": "poppins",
        "name": "Poppins",
        "family": "'Poppins', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "modern",
        "category_label": "Hiện Đại & Tinh Tế",
        "desc": "Hình học chuẩn xác, đường tròn trơn tru cực kỳ phổ biến",
        "weights": "400,500,600,700"
    },
    {
        "id": "outfit",
        "name": "Outfit",
        "family": "'Outfit', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "modern",
        "category_label": "Hiện Đại & Tinh Tế",
        "desc": "Đột phá thẩm mỹ tương lai, tinh hoa thương hiệu số",
        "weights": "400,500,600,700"
    },
    {
        "id": "manrope",
        "name": "Manrope",
        "family": "'Manrope', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "modern",
        "category_label": "Hiện Đại & Tinh Tế",
        "desc": "Sự kết hợp giữa nét hình học và grotesk hiện đại",
        "weights": "400,500,600,700"
    },
    {
        "id": "figtree",
        "name": "Figtree",
        "family": "'Figtree', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "modern",
        "category_label": "Hiện Đại & Tinh Tế",
        "desc": "Thân thiện nhưng chuẩn mực, được tin dùng trên Stripe & Linear",
        "weights": "400,500,600,700"
    },
    {
        "id": "space-grotesk",
        "name": "Space Grotesk",
        "family": "'Space Grotesk', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "modern",
        "category_label": "Hiện Đại & Tinh Tế",
        "desc": "Phong cách khoa học vũ trụ, phá cách đầy cá tính",
        "weights": "400,500,600,700"
    },
    {
        "id": "dm-sans",
        "name": "DM Sans",
        "family": "'DM Sans', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "modern",
        "category_label": "Hiện Đại & Tinh Tế",
        "desc": "Tối giản hình học, tương phản cực tốt trên nền sáng",
        "weights": "400,500,700"
    },
    {
        "id": "urbanist",
        "name": "Urbanist",
        "family": "'Urbanist', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "modern",
        "category_label": "Hiện Đại & Tinh Tế",
        "desc": "Thành thị đương đại, thanh mảnh sắc lẹm",
        "weights": "300,400,500,600,700"
    },
    {
        "id": "work-sans",
        "name": "Work Sans",
        "family": "'Work Sans', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "modern",
        "category_label": "Hiện Đại & Tinh Tế",
        "desc": "Tối ưu cho hiển thị bảng tính, số liệu và màn hình",
        "weights": "400,500,600,700"
    },
    {
        "id": "roboto",
        "name": "Roboto",
        "family": "'Roboto', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "modern",
        "category_label": "Hiện Đại & Tinh Tế",
        "desc": "Font biểu tượng của Google Android, hình học kết hợp đường cong mở",
        "weights": "400,500,700"
    },
    {
        "id": "open-sans",
        "name": "Open Sans",
        "family": "'Open Sans', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "modern",
        "category_label": "Hiện Đại & Tinh Tế",
        "desc": "Cực kỳ thân thiện và dễ đọc, được tối ưu cho cả web và in ấn",
        "weights": "400,600,700"
    },
    {
        "id": "albert-sans",
        "name": "Albert Sans",
        "family": "'Albert Sans', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "modern",
        "category_label": "Hiện Đại & Tinh Tế",
        "desc": "Phong cách Bắc Âu Scandinavian thanh nhã",
        "weights": "400,500,600,700"
    },
    {
        "id": "cabin",
        "name": "Cabin",
        "family": "'Cabin', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "modern",
        "category_label": "Hiện Đại & Tinh Tế",
        "desc": "Nhân văn học hiện đại với nét cong nhẹ ở đuôi",
        "weights": "400,500,600,700"
    },
    {
        "id": "maven-pro",
        "name": "Maven Pro",
        "family": "'Maven Pro', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "modern",
        "category_label": "Hiện Đại & Tinh Tế",
        "desc": "Nét cong uốn độc đáo, mang diện mạo sản phẩm cao cấp",
        "weights": "400,500,600,700"
    },
    {
        "id": "barlow",
        "name": "Barlow",
        "family": "'Barlow', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "modern",
        "category_label": "Hiện Đại & Tinh Tế",
        "desc": "Lấy cảm hứng từ biển số xe và hệ thống tàu điện California",
        "weights": "400,500,600,700"
    },
    {
        "id": "red-hat-display",
        "name": "Red Hat Display",
        "family": "'Red Hat Display', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "modern",
        "category_label": "Hiện Đại & Tinh Tế",
        "desc": "Được hãng công nghệ Red Hat đặt hàng riêng cho tiêu đề nổi bật",
        "weights": "400,500,600,700,900"
    },
    {
        "id": "rubik",
        "name": "Rubik",
        "family": "'Rubik', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "modern",
        "category_label": "Hiện Đại & Tinh Tế",
        "desc": "Góc bo nhẹ nhàng, mang cảm giác khối hộp vững chãi",
        "weights": "400,500,600,700"
    },
    {
        "id": "jost",
        "name": "Jost",
        "family": "'Jost', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "modern",
        "category_label": "Hiện Đại & Tinh Tế",
        "desc": "Kế thừa xuất sắc trường phái Bauhaus Futura thập niên 1920",
        "weights": "400,500,600,700"
    },

    # ==========================================
    # NHÓM 4: NGHỆ THUẬT & VIẾT TAY (16 fonts)
    # ==========================================
    {
        "id": "dancing-script",
        "name": "Dancing Script",
        "family": "'Dancing Script', 'Microsoft JhengHei', '微軟正黑體', cursive",
        "category": "script",
        "category_label": "Nghệ Thuật & Viết Tay",
        "desc": "Nhảy múa vui nhộn, nét chữ bay bổng đầy sức sống",
        "weights": "400,600,700"
    },
    {
        "id": "pacifico",
        "name": "Pacifico",
        "family": "'Pacifico', 'Microsoft JhengHei', '微軟正黑體', cursive",
        "category": "script",
        "category_label": "Nghệ Thuật & Viết Tay",
        "desc": "Văn hóa lướt sóng Mỹ thập niên 50 ngọt ngào",
        "weights": "400"
    },
    {
        "id": "great-vibes",
        "name": "Great Vibes",
        "family": "'Great Vibes', 'Microsoft JhengHei', '微軟正黑體', cursive",
        "category": "script",
        "category_label": "Nghệ Thuật & Viết Tay",
        "desc": "Thư pháp hoàng gia lộng lẫy, chuẩn thiệp cưới và chứng chỉ",
        "weights": "400"
    },
    {
        "id": "caveat",
        "name": "Caveat",
        "family": "'Caveat', 'Microsoft JhengHei', '微軟正黑體', cursive",
        "category": "script",
        "category_label": "Nghệ Thuật & Viết Tay",
        "desc": "Bút dạ ghi chú tự nhiên, chân phương và thân mật",
        "weights": "400,600,700"
    },
    {
        "id": "satisfy",
        "name": "Satisfy",
        "family": "'Satisfy', 'Microsoft JhengHei', '微軟正黑體', cursive",
        "category": "script",
        "category_label": "Nghệ Thuật & Viết Tay",
        "desc": "Bút lông mềm mượt, thanh lịch vượt thời gian",
        "weights": "400"
    },
    {
        "id": "marck-script",
        "name": "Marck Script",
        "family": "'Marck Script', 'Microsoft JhengHei', '微軟正黑體', cursive",
        "category": "script",
        "category_label": "Nghệ Thuật & Viết Tay",
        "desc": "Chữ ký tay của nghệ nhân Marck Fogel, tự nhiên không gò bó",
        "weights": "400"
    },
    {
        "id": "courgette",
        "name": "Courgette",
        "family": "'Courgette', 'Microsoft JhengHei', '微軟正黑體', cursive",
        "category": "script",
        "category_label": "Nghệ Thuật & Viết Tay",
        "desc": "Bút cọ đậm đà, rất bắt mắt ngay cả ở kích thước vừa phải",
        "weights": "400"
    },
    {
        "id": "kaushan-script",
        "name": "Kaushan Script",
        "family": "'Kaushan Script', 'Microsoft JhengHei', '微軟正黑體', cursive",
        "category": "script",
        "category_label": "Nghệ Thuật & Viết Tay",
        "desc": "Nét cọ thô mộc xước vệt, đậm phong cách nghệ thuật đường phố",
        "weights": "400"
    },
    {
        "id": "bad-script",
        "name": "Bad Script",
        "family": "'Bad Script', 'Microsoft JhengHei', '微軟正黑體', cursive",
        "category": "script",
        "category_label": "Nghệ Thuật & Viết Tay",
        "desc": "Bút mực viết nhanh, phóng khoáng và ngẫu hứng",
        "weights": "400"
    },
    {
        "id": "yellowtail",
        "name": "Yellowtail",
        "family": "'Yellowtail', 'Microsoft JhengHei', '微軟正黑體', cursive",
        "category": "script",
        "category_label": "Nghệ Thuật & Viết Tay",
        "desc": "Chữ biển hiệu cổ điển thập niên 1930 với góc nghiêng duyên dáng",
        "weights": "400"
    },
    {
        "id": "alex-brush",
        "name": "Alex Brush",
        "family": "'Alex Brush', 'Microsoft JhengHei', '微軟正黑體', cursive",
        "category": "script",
        "category_label": "Nghệ Thuật & Viết Tay",
        "desc": "Thư pháp nét cọ thanh thoát, chữ hoa kiêu sa ấn tượng",
        "weights": "400"
    },
    {
        "id": "allura",
        "name": "Allura",
        "family": "'Allura', 'Microsoft JhengHei', '微軟正黑體', cursive",
        "category": "script",
        "category_label": "Nghệ Thuật & Viết Tay",
        "desc": "Nét chỉ thêu mềm mại, nữ tính và cực kỳ trau chuốt",
        "weights": "400"
    },
    {
        "id": "tangerine",
        "name": "Tangerine",
        "family": "'Tangerine', 'Microsoft JhengHei', '微軟正黑體', cursive",
        "category": "script",
        "category_label": "Nghệ Thuật & Viết Tay",
        "desc": "Chữ nghiêng Ý thanh mảnh như tranh khắc lụa",
        "weights": "400,700"
    },
    {
        "id": "sacramento",
        "name": "Sacramento",
        "family": "'Sacramento', 'Microsoft JhengHei', '微軟正黑體', cursive",
        "category": "script",
        "category_label": "Nghệ Thuật & Viết Tay",
        "desc": "Nét đơn dòng monoline duyên dáng của thập niên 50",
        "weights": "400"
    },
    {
        "id": "amita",
        "name": "Amita",
        "family": "'Amita', 'Microsoft JhengHei', '微軟正黑體', cursive",
        "category": "script",
        "category_label": "Nghệ Thuật & Viết Tay",
        "desc": "Giao thoa nét bút truyền thống và thiết kế hiện đại",
        "weights": "400,700"
    },
    {
        "id": "parisienne",
        "name": "Parisienne",
        "family": "'Parisienne', 'Microsoft JhengHei', '微軟正黑體', cursive",
        "category": "script",
        "category_label": "Nghệ Thuật & Viết Tay",
        "desc": "Thanh lịch như quý cô Paris rảo bước trên đại lộ Champs-Élysées",
        "weights": "400"
    },

    # ==========================================
    # NHÓM 5: HÌNH HỌC & TỐI GIẢN (14 fonts)
    # ==========================================
    {
        "id": "syne",
        "name": "Syne",
        "family": "'Syne', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "geometric",
        "category_label": "Hình Học & Tối Giản",
        "desc": "Nghệ thuật đương đại Pháp, bề ngang chữ rộng độc lạ",
        "weights": "400,600,700,800"
    },
    {
        "id": "sora",
        "name": "Sora",
        "family": "'Sora', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "geometric",
        "category_label": "Hình Học & Tối Giản",
        "desc": "Hình học sắc nét thiết kế riêng cho lĩnh vực tiền mã hóa và AI",
        "weights": "400,600,700"
    },
    {
        "id": "epilogue",
        "name": "Epilogue",
        "family": "'Epilogue', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "geometric",
        "category_label": "Hình Học & Tối Giản",
        "desc": "Đậm chất thiết kế đồ họa độc lập, góc chữ vuông vắn chuẩn xác",
        "weights": "400,600,700,800"
    },
    {
        "id": "archivo",
        "name": "Archivo",
        "family": "'Archivo', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "geometric",
        "category_label": "Hình Học & Tối Giản",
        "desc": "Được thiết kế cho tiêu đề lớn và áp phích kiến trúc",
        "weights": "400,600,700"
    },
    {
        "id": "lexend-deca",
        "name": "Lexend Deca",
        "family": "'Lexend Deca', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "geometric",
        "category_label": "Hình Học & Tối Giản",
        "desc": "Khoảng cách ký tự được nới rộng tối ưu cho mắt quét nhanh",
        "weights": "400"
    },
    {
        "id": "overpass",
        "name": "Overpass",
        "family": "'Overpass', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "geometric",
        "category_label": "Hình Học & Tối Giản",
        "desc": "Dựa trên font biển chỉ dẫn cao tốc quốc lộ Highway Gothic",
        "weights": "400,600,700"
    },
    {
        "id": "questrial",
        "name": "Questrial",
        "family": "'Questrial', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "geometric",
        "category_label": "Hình Học & Tối Giản",
        "desc": "Vòng tròn hoàn mỹ lấy cảm hứng từ phong cách Thụy Sĩ",
        "weights": "400"
    },
    {
        "id": "kanit",
        "name": "Kanit",
        "family": "'Kanit', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "geometric",
        "category_label": "Hình Học & Tối Giản",
        "desc": "Đường nét thẳng dứt khoát kết hợp bo cong hiện đại",
        "weights": "400,500,600,700"
    },
    {
        "id": "bai-jamjuree",
        "name": "Bai Jamjuree",
        "family": "'Bai Jamjuree', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "geometric",
        "category_label": "Hình Học & Tối Giản",
        "desc": "Hình dáng vuông bo tròn góc đậm chất công nghệ thế hệ mới",
        "weights": "400,500,600,700"
    },
    {
        "id": "chakra-petch",
        "name": "Chakra Petch",
        "family": "'Chakra Petch', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "geometric",
        "category_label": "Hình Học & Tối Giản",
        "desc": "Góc vát đa giác cơ khí sắc cạnh, thích hợp IoT và tự động hóa",
        "weights": "400,600,700"
    },
    {
        "id": "teko",
        "name": "Teko",
        "family": "'Teko', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "geometric",
        "category_label": "Hình Học & Tối Giản",
        "desc": "Thân hẹp cao vút, rất uy lực trong các banner quảng cáo",
        "weights": "400,600,700"
    },
    {
        "id": "anton",
        "name": "Anton",
        "family": "'Anton', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "geometric",
        "category_label": "Hình Học & Tối Giản",
        "desc": "Font áp phích truyền thống tái sinh cho thời đại web",
        "weights": "400"
    },
    {
        "id": "oswald",
        "name": "Oswald",
        "family": "'Oswald', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "geometric",
        "category_label": "Hình Học & Tối Giản",
        "desc": "Kế thừa phong cách gothic cổ điển, thẳng đứng và cứng cáp",
        "weights": "400,500,600,700"
    },
    {
        "id": "bebas-neue",
        "name": "Bebas Neue",
        "family": "'Bebas Neue', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "geometric",
        "category_label": "Hình Học & Tối Giản",
        "desc": "Ông vua của các dòng font tiêu đề in hoa toàn phần",
        "weights": "400"
    },

    # ==========================================
    # NHÓM 6: CÔNG NGHỆ & TƯƠNG LAI (12 fonts)
    # ==========================================
    {
        "id": "fira-code",
        "name": "Fira Code",
        "family": "'Fira Code', 'Microsoft JhengHei', '微軟正黑體', monospace",
        "category": "tech",
        "category_label": "Công Nghệ & Tương Lai",
        "desc": "Font đơn khoảng cho lập trình viên với ký hiệu nối ligature đỉnh cao",
        "weights": "400,500,600,700"
    },
    {
        "id": "jetbrains-mono",
        "name": "JetBrains Mono",
        "family": "'JetBrains Mono', 'Microsoft JhengHei', '微軟正黑體', monospace",
        "category": "tech",
        "category_label": "Công Nghệ & Tương Lai",
        "desc": "Được tạo riêng bởi JetBrains để tối ưu mắt khi đọc mã nguồn dài",
        "weights": "400,600,700"
    },
    {
        "id": "space-mono",
        "name": "Space Mono",
        "family": "'Space Mono', 'Microsoft JhengHei', '微軟正黑體', monospace",
        "category": "tech",
        "category_label": "Công Nghệ & Tương Lai",
        "desc": "Cảm hứng văn bản máy in điện toán thập niên 60",
        "weights": "400,700"
    },
    {
        "id": "roboto-mono",
        "name": "Roboto Mono",
        "family": "'Roboto Mono', 'Microsoft JhengHei', '微軟正黑體', monospace",
        "category": "tech",
        "category_label": "Công Nghệ & Tương Lai",
        "desc": "Phiên bản monospace chuẩn chỉnh của gia đình Roboto",
        "weights": "400,500,700"
    },
    {
        "id": "source-code-pro",
        "name": "Source Code Pro",
        "family": "'Source Code Pro', 'Microsoft JhengHei', '微軟正黑體', monospace",
        "category": "tech",
        "category_label": "Công Nghệ & Tương Lai",
        "desc": "Font lập trình chuyên nghiệp của Adobe, cực kỳ cân đối",
        "weights": "400,600,700"
    },
    {
        "id": "share-tech-mono",
        "name": "Share Tech Mono",
        "family": "'Share Tech Mono', 'Microsoft JhengHei', '微軟正黑體', monospace",
        "category": "tech",
        "category_label": "Công Nghệ & Tương Lai",
        "desc": "Màn hình radar phòng điều khiển quân sự và IoT trung tâm",
        "weights": "400"
    },
    {
        "id": "vt323",
        "name": "VT323",
        "family": "'VT323', 'Microsoft JhengHei', '微軟正黑體', monospace",
        "category": "tech",
        "category_label": "Công Nghệ & Tương Lai",
        "desc": "Mô phỏng thiết bị đầu cuối DEC VT220 retro hoài niệm",
        "weights": "400"
    },
    {
        "id": "orbitron",
        "name": "Orbitron",
        "family": "'Orbitron', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "tech",
        "category_label": "Công Nghệ & Tương Lai",
        "desc": "Đậm chất phi thuyền không gian khoa học viễn tưởng Sci-Fi",
        "weights": "400,600,700,900"
    },
    {
        "id": "exo-2",
        "name": "Exo 2",
        "family": "'Exo 2', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "tech",
        "category_label": "Công Nghệ & Tương Lai",
        "desc": "Thiết kế vị lai nhưng rất mượt và giàu cảm xúc",
        "weights": "400,600,700"
    },
    {
        "id": "audiowide",
        "name": "Audiowide",
        "family": "'Audiowide', 'Microsoft JhengHei', '微軟正黑體', cursive",
        "category": "tech",
        "category_label": "Công Nghệ & Tương Lai",
        "desc": "Công nghệ âm thanh nổi và điện tử tương lai",
        "weights": "400"
    },
    {
        "id": "michroma",
        "name": "Michroma",
        "family": "'Michroma', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "tech",
        "category_label": "Công Nghệ & Tương Lai",
        "desc": "Bảng đồng hồ taplo siêu xe và phi thuyền thế kỷ 21",
        "weights": "400"
    },
    {
        "id": "russo-one",
        "name": "Russo One",
        "family": "'Russo One', 'Microsoft JhengHei', '微軟正黑體', sans-serif",
        "category": "tech",
        "category_label": "Công Nghệ & Tương Lai",
        "desc": "Khối chữ dày dặn như lớp giáp thép robot cơ giới",
        "weights": "400"
    }
]


def get_all_fonts() -> List[Dict[str, Any]]:
    """Return all 100 configured fonts."""
    return FONT_COLLECTION


def get_active_font_setting() -> Dict[str, Any]:
    """Read active font setting from file or return default Merriweather."""
    if FONT_SETTINGS_FILE.exists():
        try:
            with open(FONT_SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "name" in data:
                    return data
        except Exception:
            pass

    return {
        "id": "merriweather",
        "name": "Merriweather",
        "family": "'Merriweather', 'Microsoft JhengHei', '微軟正黑體', serif",
        "category": "serif",
        "category_label": "Thanh Lịch & Sang Trọng"
    }


def save_active_font_setting(font_data: Dict[str, Any]) -> Dict[str, Any]:
    """Persist active font selection to local JSON config."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    setting = {
        "id": font_data.get("id", "merriweather"),
        "name": font_data.get("name", "Merriweather"),
        "family": font_data.get("family", "'Merriweather', 'Microsoft JhengHei', serif"),
        "category": font_data.get("category", "serif"),
        "category_label": font_data.get("category_label", "Thanh Lịch & Sang Trọng")
    }
    with open(FONT_SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(setting, f, ensure_ascii=False, indent=2)
    return setting
