# Quick Start: Class-Section Filter

## 🚀 5-Minute Setup

### 1. Apply Database Migration (Required)
```bash
alembic upgrade head
```

### 2. Restart Application
```bash
# Docker
docker-compose restart

# Local
python -m uvicorn src.app.main:app --reload
```

### 3. Open Web Interface
```
http://localhost:8000
```

---

## 📝 Quick Usage Guide

### Enroll Student with Class/Section

**Web UI:**
1. Enter name: `John Doe`
2. Select class: `10th`
3. Select section: `A`
4. Click `Guided Enroll`

**Result:** Student enrolled with class/section metadata

---

### Apply Recognition Filter

**Web UI:**
1. Go to "🎯 Class & Section Filter" section
2. Select class: `10th`
3. Select section: `A`
4. Click `Apply Filter`
5. See: `✅ Cached Students: 45`

**Result:** Only 10th-A students are now recognized

---

### Clear Filter (All Students)

**Web UI:**
1. Click `Clear Filter` button

**Result:** All students back in cache

---

## 🎯 Performance Example

### Before Filter
- 500 students loaded
- 150ms recognition time
- 80 MB memory

### After Filter (10th-A only)
- 45 students loaded
- 15ms recognition time
- 7 MB memory

**10× faster recognition!**

---

## 🔧 API Quick Reference

```bash
# Enroll with class/section
curl -X POST http://localhost:8000/api/enroll \
  -F "name=John Doe" \
  -F "class_name=10th" \
  -F "section_name=A" \
  -F "files=@photo.jpg"

# Apply filter
curl -X POST "http://localhost:8000/api/filter?class_name=10th&section_name=A"

# Get available classes
curl http://localhost:8000/api/classes

# Get available sections
curl http://localhost:8000/api/sections
```

---

## ✅ Verification Checklist

- [ ] Migration applied successfully
- [ ] Class/Section filter section visible in UI
- [ ] Dropdowns appear in enrollment forms
- [ ] Can enroll student with class/section
- [ ] Apply filter reduces cached student count
- [ ] Recognition works after filter applied

---

## 📚 More Information

- **Full Guide:** `CLASS_SECTION_FILTER_GUIDE.md`
- **Implementation Details:** `CLASS_SECTION_IMPLEMENTATION.md`
- **Migration Script:** `alembic/versions/002_add_class_section_columns.py`
- **Utility Script:** `scripts/populate_class_sections.py`

---

## 🆘 Troubleshooting

**Dropdowns empty?**
→ Enroll at least one student with class/section

**Filter not working?**
→ Check browser console, verify migration applied

**Old students not appearing?**
→ Select "All Classes" to include students without classification

---

## 💡 Pro Tips

1. Apply filter **before** starting recognition
2. Use consistent naming for classes/sections
3. Re-apply filter after enrolling new students
4. Clear filter when recognizing across multiple classes

---

**Ready to use!** 🎉
