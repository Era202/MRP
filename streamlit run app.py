# ==============================================================================
# MRP Analysis Tool Final Version with Stock Analysis and Component Order Type
# Developed by: Reda Roshdy
# Date: 17-Sep-2025
# ==============================================================================

# -------------------------------
# 1. استدعاء المكتبات اللازمة
# -------------------------------
import streamlit as st
import pandas as pd
import datetime
from io import BytesIO
import zipfile
import calendar
import plotly.express as px


# ==============================================================================
# 2. إعداد التكوين والأعمدة (تحسين جديد)
# ==============================================================================

COLUMN_NAMES = {
    "material": ["Material", "Item", "code", "Code", "المادة", "Product"],
    "material_desc": ["Material Description", "Description", "وصف"],
    "order_type": ["Order Type", "OT", "نوع الطلب", "Sales Org."],
    "component": ["Component", "Comp", "المكون"],
    "component_desc": ["Component Description", "Comp Desc", " المسمى", "وصف المكون"],
    "component_uom": ["Component UoM", "UoM", "الوحدة"],
    "component_qty": ["Component Quantity", "Qty", "كمية المكون"],
    "mrp_controller": ["MRP Contor", "MRP Controller", "مسؤول MRP"],
    "current_stock": ["Current Stock", "Stock", "المخزون الحالي", "Unrestricted"],
    "component_order_type": ["Component Order Type", "Order Category", "نوع أمر المكون", "Procurement Type"],
    "hierarchy_level": ["Hierarchy Level", "Level", "المستوى الهرمي"]
}

# ==============================================================================
# 3. الدوال المساعدة (Functions)
# ==============================================================================
def col(name_key):
    return COLUMN_NAMES[name_key][0]

def normalize_columns(df, column_map):
    rename_dict = {}
    for key, aliases in column_map.items():
        if isinstance(aliases, list):
            for alias in aliases:
                if alias in df.columns:
                    rename_dict[alias] = aliases[0]
        else:
            if aliases in df.columns:
                rename_dict[aliases] = aliases
    return df.rename(columns=rename_dict)

@st.cache_data
def load_and_validate_data(uploaded_file):
    try:
        xls = pd.ExcelFile(uploaded_file, engine='openpyxl')

        required_sheets = ["plan", "Component"]
        missing_sheets = [sheet for sheet in required_sheets if sheet not in xls.sheet_names]
        if missing_sheets:
            st.error(f"❌ الملف لا يحتوي على الأوراق المطلوبة: {', '.join(missing_sheets)}")
            st.stop()
            
        plan_df = normalize_columns(xls.parse("plan"), COLUMN_NAMES)
        component_df = normalize_columns(xls.parse("Component"), COLUMN_NAMES)
        mrp_df = normalize_columns(xls.parse("MRP Contor"), COLUMN_NAMES) if "MRP Contor" in xls.sheet_names else pd.DataFrame()

        # التحقق من الأعمدة الأساسية
        required_plan_columns = [col("material"), col("material_desc"), col("order_type")]
        if not all(c in plan_df.columns for c in required_plan_columns):
            st.error(f"❌ جدول الخطة لا يحتوي على الأعمدة المطلوبة: {', '.join(required_plan_columns)}")
            st.stop()

        required_component_columns = [col("material"), col("component"), col("component_qty")]
        if not all(c in component_df.columns for c in required_component_columns):
            st.error(f"❌ جدول المكونات لا يحتوي على الأعمدة المطلوبة: {', '.join(required_component_columns)}")
            st.stop()

        # التحقق من وجود أعمدة اختيارية
        if col("current_stock") not in component_df.columns:
            component_df[col("current_stock")] = 0

        if col("component_order_type") not in component_df.columns:
            component_df[col("component_order_type")] = "غير محدد"
        
        if col("hierarchy_level") not in component_df.columns:
            component_df[col("hierarchy_level")] = "غير محدد"

        return plan_df, component_df, mrp_df

    except Exception as e:
        st.error(f"حدث خطأ أثناء قراءة الملف: {e}")
        st.stop()


# ==============================================================================
# 4. واجهة المستخدم الرئيسية للتطبيق
# ==============================================================================

st.set_page_config(page_title="🔥 MRP Tool", page_icon="📂", layout="wide")
st.header("📂 الاصدار الذكى من البرنامج لتحليل واستخراج وحفظ نتائج الـ MRP")
st.markdown("<p style='font-size:16px; font-weight:bold;'>📂 اختر ملف الخطة الشهرية Excel</p>", unsafe_allow_html=True)

uploaded_file = st.file_uploader("", type=["xlsx"])

if uploaded_file:
    plan_df, component_df, mrp_df = load_and_validate_data(uploaded_file)
    plan_df_orig = plan_df.copy()
    component_df_orig = component_df.copy()
    mrp_df_orig = mrp_df.copy()

    # أي معالجة أو جداول Pivot بعد كده...

    # استخراج أعمدة التواريخ مرة واحدة
    date_cols = [c for c in plan_df.columns if isinstance(c, (datetime.datetime, pd.Timestamp))]
    
    # نسخة معالجة
    plan_df_processed = plan_df.copy()

    # 🔹 إجبار أعمدة الأكواد إنها تبقى نصوص لتفادي الفواصل

    with st.spinner("⏳ جاري معالجة البيانات وعرض النتائج..."):
        # (نفس الحسابات والجداول والرسوم البيانية الموجودة في كودك الأصلي بدون تعديل)
         # -------------------------------
        # تجهيز البيانات الأساسية
        # -------------------------------
        plan_melted = plan_df.melt(
            id_vars=["Material", "Material Description", "Order Type"],
            var_name="Date",
            value_name="Planned Quantity"
        )
        plan_melted["Date"] = pd.to_datetime(plan_melted["Date"], errors='coerce')
        merged_df = pd.merge(plan_melted, component_df, on="Material", how="left")
        merged_df["Required Component Quantity"] = merged_df["Planned Quantity"] * merged_df["Component Quantity"]

        # -------------------------------
        # الملخص السريع (عرض فقط)
        # -------------------------------
        total_models = plan_df["Material"].nunique()
        total_components = component_df["Component"].nunique()
        total_boms = len(component_df)
        empty_mrp_count = mrp_df["Component"].isna().sum() if not mrp_df.empty else 0

        diff_uom = component_df.groupby("Component")["Component UoM"].nunique()
        diff_uom = diff_uom[diff_uom > 1]
        total_diff_uom = len(diff_uom)

        if total_diff_uom > 0:
            diff_uom_str = ", ".join(map(str, diff_uom.index))
            diff_uom_color = "red"
        else:
            diff_uom_str = "لا يوجد"
            diff_uom_color = "green"

        missing_boms = set(plan_df["Material"]) - set(component_df["Material"])
        total_missing_boms = len(missing_boms)
        missing_boms_html = (
            f"<span style='color:red;'>{', '.join(map(str, missing_boms))}</span>"
            if missing_boms else "<span style='color:green;'>لا يوجد</span>"
        )

        # إحصائية جديدة لأنواع طلب المكونات
       # purchase_count = len(component_df[component_df[COLUMN_NAMES["component_order_type"]] == "شراء"])
        #manufacturing_count = len(component_df[component_df[COLUMN_NAMES["component_order_type"]] == "تصنيع"])
        #undefined_count = len(component_df[component_df[COLUMN_NAMES["component_order_type"]] == "غير محدد"])


        # -------------------------------
        # إحصائية جديدة لأنواع طلب المكونات
        # -------------------------------

        # خريطة الأكواد إلى النصوص
        order_type_map = {
            "F": "شراء",
            "E": "تصنيع"
        }

        # إضافة عمود جديد بالوصف العربي
        component_df["Order_Type_Label"] = component_df["Component Order Type"].map(order_type_map).fillna("غير محدد")

        # حساب الإحصائيات
        purchase_count = (component_df["Order_Type_Label"] == "شراء").sum()         # عدد المكونات شراء
        manufacturing_count = (component_df["Order_Type_Label"] == "تصنيع").sum()   # عدد المكونات تصنيع
        undefined_count = (component_df["Order_Type_Label"] == "غير محدد").sum()    # عدد المكونات غير محددة

        st.markdown(f"""
        <div style="direction:rtl; text-align:right; font-size:20px;">
        <span style="font-size:22px; color:#1976d2;">📌 <b>ملخص نتائج الخطة </b></span>
        <br><br>
        <ul style="list-style-type:none; padding-right:0;">

          <li>🟢 <b>{total_models}</b> موديلات بوتاجاز بالخطة</li>
          <li>🔵 <b>{total_components}</b> عدد المكونات المستخدمة</li>
          <li>🟠 <b>{total_boms}</b> إجمالي عدد مكونات الـ BOMs</li>

          <li>{"❌" if empty_mrp_count>0 else "✅"} 
              <b style="color:{'red' if empty_mrp_count>0 else 'green'};">
              {empty_mrp_count}</b> مكونات بدون MRP Contor</li>

          <li>{"⚠️" if total_diff_uom>0 else "✅"} 
              <b style="color:{'red' if total_diff_uom>0 else 'green'};">
              {total_diff_uom}</b> مكونات لها أكثر من وحدة: 
              <span style="color:{diff_uom_color};">{diff_uom_str}</span>
          </li>

          <li>{"⚠️" if total_missing_boms>0 else "✅"} 
              <b style="color:{'red' if total_missing_boms>0 else 'green'};">
              {total_missing_boms}</b> منتجات موجودة بالخطة لكن بدون BOM: 
              {missing_boms_html}
          </li>

        </ul>
        </div>
        """, unsafe_allow_html=True)

        # عرض إحصائية أنواع طلب المكونات
        st.markdown(f"""
        <div style="direction:rtl; text-align:right; font-size:20px;">
        <span style="font-size:22px; color:#1976d2;">🔹 <b>ملخص أنواع طلب المكونات</b></span>
        <br><br>
        <ul style="list-style-type:none; padding-right:0;">
            <li>🛒 <b>{purchase_count}</b> مكونات شراء</li>
            <li>🏭 <b>{manufacturing_count}</b> مكونات تصنيع</li>
            <li>❓ <b>{undefined_count}</b> مكونات غير محددة</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)

        # -------------------------------
        # Need_By_Date
        # -------------------------------
        result_date = merged_df.groupby(
            ["Component", "Component Description", "Component UoM", "Current Stock", "Component Order Type", "Date"]
        )["Required Component Quantity"].sum().reset_index()

        pivot_by_date = result_date.pivot_table(
            index=["Component", "Component Description", "Component UoM", "Current Stock", "Component Order Type"],
            columns="Date",
            values="Required Component Quantity",
            aggfunc="sum",
            fill_value=0
        ).reset_index()

        if not mrp_df.empty:
            pivot_by_date = pd.merge(
                pivot_by_date,
                mrp_df[["Component", "MRP Contor"]],
                on="Component",
                how="left"
            )

            # إعادة ترتيب الأعمدة
            cols = pivot_by_date.columns.tolist()
            fixed_order = ["Component", "Component Description", "MRP Contor", "Component UoM", "Current Stock", "Component Order Type"]
            other_cols = [c for c in cols if c not in fixed_order]
            pivot_by_date = pivot_by_date[fixed_order + other_cols]

        # تنسيق أسماء الأعمدة (التواريخ تبقى dd mmm)
        pivot_by_date.columns = [
            col.strftime("%d %b") if isinstance(col, pd.Timestamp) else col
            for col in pivot_by_date.columns
        ]

        # -------------------------------
        # Need_By_Order Type
        # -------------------------------
        result_order = merged_df.groupby(
            ["Component", "Component Description", "Component UoM", "Current Stock", "Component Order Type", "Order Type", "Date"]
        )["Required Component Quantity"].sum().reset_index()

        pivot_by_order = result_order.pivot_table(
            index=["Component", "Component Description", "Component UoM", "Current Stock", "Component Order Type"],
            columns=["Date", "Order Type"],
            values="Required Component Quantity",
            aggfunc="sum",
            fill_value=0
        ).reset_index()

        pivot_by_order.columns = [
            f"{col[1][0]} - {col[0].strftime('%d %b')}" if isinstance(col, tuple) and isinstance(col[0], pd.Timestamp)
            else col if isinstance(col, str) else col[0]
            for col in pivot_by_order.columns
        ]

        # 🔹 إضافة عمود MRP Contor
        if not mrp_df.empty:
            pivot_by_order = pivot_by_order.merge(mrp_df[["Component", "MRP Contor"]], on="Component", how="left")

            merged_df = merged_df.merge(mrp_df[["Component", "MRP Contor"]], on="Component", how="left")

            component_bom_map = merged_df.groupby(
                ["MRP Contor", "Component", "Material", "Component Order Type"]
            ).agg({
                "Order Type": lambda x: ','.join(sorted(set(x))),
                "Planned Quantity": "sum"
            }).reset_index()

            component_bom_map["OrderType_Quantity"] = component_bom_map["Order Type"] + " (" + component_bom_map["Planned Quantity"].astype(str) + ")"

            component_bom_pivot = component_bom_map.pivot_table(
                index=["MRP Contor", "Component", "Component Order Type"],
                columns="Material",
                values="OrderType_Quantity",
                aggfunc=lambda x: ','.join(x),
                fill_value=""
            )

        # -------------------------------
        # تحليل الرصيد والمكونات الحرجة مع فلتر MRP Contor ونوع الطلب
        # -------------------------------
        st.markdown("---")
        st.subheader("📊 تحليل حرجية الرصيد ونسبة التغطية")

        # حساب إجمالي الاحتياج والرصيد لكل مكون
        component_analysis = merged_df.groupby([
            "Component", "Component Description", "Component UoM", 
            "Current Stock", "Component Order Type", "Hierarchy Level"
        ]).agg({
            "Required Component Quantity": "sum",
            "Order Type": lambda x: ", ".join(sorted(set(x)))
        }).reset_index()

        # دمج بيانات MRP Contor إذا كانت موجودة
        if not mrp_df.empty:
            component_analysis = pd.merge(
                component_analysis,
                mrp_df[["Component", "MRP Contor"]],
                on="Component",
                how="left"
            )
            # استبدال القيم الفارغة بـ "غير محدد"
            component_analysis["MRP Contor"] = component_analysis["MRP Contor"].fillna("غير محدد")
        else:
            component_analysis["MRP Contor"] = "غير محدد"

        # حساب نسبة التغطية
        component_analysis["Coverage Percentage"] = (component_analysis["Current Stock"] / component_analysis["Required Component Quantity"] * 100).round(1)
        component_analysis["Coverage Status"] = component_analysis["Coverage Percentage"].apply(
            lambda x: "🟢 كافية" if x >= 100 else "🟡 جزئية" if x >= 50 else "🔴 غير كافية"
        )

        # تحديد الأولوية بناء على نسبة التغطية والكمية المطلوبة
        component_analysis["Priority"] = component_analysis.apply(
            lambda row: "🔥 عاجل" if row["Coverage Percentage"] < 30 and row["Required Component Quantity"] > 1000 
            else "⚠️ متوسط" if row["Coverage Percentage"] < 50 
            else "✅ منخفض", 
            axis=1
        )
        # ----- فلاتر المستخدم -----
        mrp_controllers = sorted(component_analysis[col("mrp_controller")].dropna().unique())
        selected_mrp = st.multiselect("🔍 تصفية حسب MRP Contor:", options=mrp_controllers, default=mrp_controllers, help="اختر واحد أو أكثر من MRP Contor لعرضها")

        component_order_types = sorted(component_analysis[col("component_order_type")].dropna().unique())
        selected_order_types = st.multiselect("🔍 تصفية حسب نوع طلب المكون:", options=component_order_types, default=component_order_types,
            help="اختر نوع طلب المكون (شراء/تصنيع/غير محدد)")

        hierarchy_levels = sorted(component_analysis[col("hierarchy_level")].dropna().unique())
        selected_levels = st.multiselect("🔍 تصفية حسب المستوى الهرمي (Hierarchy Level):", options=hierarchy_levels, default=hierarchy_levels, help="اختر واحد أو أكثر من المستوى لعرضها")
        # تطبيق الفلتر معاً
        filtered_analysis = component_analysis[
            (component_analysis[col("mrp_controller")].isin(selected_mrp)) &
            (component_analysis[col("component_order_type")].isin(selected_order_types)) &
            (component_analysis[col("hierarchy_level")].isin(selected_levels))
        ]


        # عرض جدول التحليل
        st.dataframe(filtered_analysis.sort_values("Coverage Percentage"))

        # إحصائيات ونسب التغطية بعد التصفية
        total_components = len(filtered_analysis)
        sufficient_coverage = len(filtered_analysis[filtered_analysis["Coverage Percentage"] >= 100])
        partial_coverage = len(filtered_analysis[(filtered_analysis["Coverage Percentage"] >= 50) & (filtered_analysis["Coverage Percentage"] < 100)])
        insufficient_coverage = len(filtered_analysis[filtered_analysis["Coverage Percentage"] < 50])
        critical_components = len(filtered_analysis[filtered_analysis["Priority"] == "🔥 عاجل"])

        st.markdown(f"""
        <div style="direction:rtl; text-align:right; font-size:18px;">
        <span style="font-size:20px; color:#1976d2;">📈 <b>إحصائيات نسبة التغطية</b></span>
        <br><br>
        <ul style="list-style-type:none; padding-right:0;">
            <li>🟢 <b>{sufficient_coverage}</b> مكونات ذات تغطية كافية ({sufficient_coverage/total_components*100:.1f}%)</li>
            <li>🟡 <b>{partial_coverage}</b> مكونات ذات تغطية جزئية ({partial_coverage/total_components*100:.1f}%)</li>
            <li>🔴 <b>{insufficient_coverage}</b> مكونات ذات تغطية غير كافية ({insufficient_coverage/total_components*100:.1f}%)</li>
            <li>🔥 <b style="color:red;">{critical_components}</b> مكونات حرجة تحتاج اهتمام عاجل</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)

        # تحليل إضافي لنوع طلب المكون
        st.markdown("---")
        st.subheader("📊 تحليل المكونات حسب نوع الطلب")

        order_type_stats = filtered_analysis.groupby("Component Order Type").agg({
            "Component": "count",
            "Required Component Quantity": "sum",
            "Current Stock": "sum"
        }).reset_index()

        order_type_stats["Coverage Percentage"] = (order_type_stats["Current Stock"] / order_type_stats["Required Component Quantity"] * 100).round(1)

        st.dataframe(order_type_stats)

        # المكونات الحرجة التي تحتاج اهتمام عاجل بعد التصفية
        critical_items = filtered_analysis[filtered_analysis["Priority"] == "🔥 عاجل"]
        if not critical_items.empty:
            st.error("🚨 المكونات الحرجة التي تحتاج إلى اهتمام عاجل:")
            st.dataframe(critical_items[["Component", "Component Description", "MRP Contor", "Component Order Type", "Current Stock", "Required Component Quantity", "Coverage Percentage", "Priority"]])
        else:
            st.success("✅ لا توجد مكونات حرجة تحتاج إلى اهتمام عاجل")

        # رسم بياني لتوزيع نسبة التغطية حسب MRP Contor
        if len(selected_mrp) > 0:
            fig_coverage = px.pie(
                filtered_analysis, 
                names="Coverage Status", 
                title="توزيع المكونات حسب حالة التغطية",
                color="Coverage Status",
                color_discrete_map={"🟢 كافية": "green", "🟡 جزئية": "orange", "🔴 غير كافية": "red"}
            )
            st.plotly_chart(fig_coverage, use_container_width=True)

        # رسم بياني للمكونات الأكثر حرجية مرتبة حسب كمية الطلب
        top_critical = filtered_analysis.nsmallest(10, "Coverage Percentage")
        if not top_critical.empty:
            # تحويل الأعمدة إلى نص قبل الدمج
            top_critical = top_critical.copy()
            top_critical["Component"] = top_critical["Component"].astype(str)
            top_critical["Component Description"] = top_critical["Component Description"].astype(str)
            
            # إنشاء تسمية مختصرة تجمع بين الكود والوصف
            top_critical["Short_Label"] = top_critical["Component"] + " - " + top_critical["Component Description"].str[:20]
            
            # ترتيب المكونات حسب كمية الطلب (من الأكبر إلى الأصغر)
            top_critical = top_critical.sort_values("Required Component Quantity", ascending=True)
            
            fig_critical = px.bar(
                top_critical,
                y="Short_Label",  # التسمية المختصرة على المحور Y
                x="Required Component Quantity",  # كمية الطلب على المحور X
                color="Coverage Percentage",  # التلوين حسب نسبة التغطية
                orientation='h',  # رسم أفقي
                title="أقل 10 مكونات في نسبة التغطية (مرتبة حسب كمية الطلب)",
                labels={
                    "Required Component Quantity": "كمية الطلب المطلوبة", 
                    "Short_Label": "المكون", 
                    "Coverage Percentage": "نسبة التغطية %",
                    "MRP Contor": "MRP Controller"
                },
                hover_data={
                    "Component": True,
                    "Component Description": True,
                    "Current Stock": True,
                    "Coverage Percentage": ":.1f",
                    "MRP Contor": True,
                    "Component Order Type": True
                },
                color_continuous_scale="RdYlGn_r"  # مقياس ألوان عكسي (أحمر للأقل تغطية)
            )
            
            # تخصيص التنسيق
            fig_critical.update_traces(
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "الوصف: %{customdata[1]}<br>"
                    "الرصيد الحالي: %{customdata[2]:,}<br>"
                    "الطلب المطلوب: %{x:,}<br>"
                    "نسبة التغطية: %{customdata[3]:.1f}%<br>"
                    "MRP Controller: %{customdata[4]}<br>"
                    "نوع الطلب: %{customdata[5]}"
                )
            )
            
            # تحسين تخطيط الرسم البياني
            fig_critical.update_layout(
                yaxis={'categoryorder':'total ascending'},  # ترتيب حسب القيمة
                xaxis_title="كمية الطلب المطلوبة",
                yaxis_title="المكون",
                hovermode="closest",
                coloraxis_colorbar=dict(title="نسبة التغطية %"),
                height=500  # زيادة الارتفاع لعرض أفضل
            )
            
            # إضافة تسميات القيم على الأعمدة
            fig_critical.update_traces(
                text=top_critical["Required Component Quantity"].apply(lambda x: f"{x:,.0f}"),
                textposition='outside'
            )
            
            st.plotly_chart(fig_critical, use_container_width=True)

        # رسم بياني إضافي لتوزيع المكونات حسب MRP Contor والحالة
        if len(selected_mrp) > 0:
            fig_mrp_coverage = px.sunburst(
                filtered_analysis,
                path=['MRP Contor', 'Coverage Status'],
                values='Required Component Quantity',
                title='توزيع المكونات حسب MRP Contor وحالة التغطية'
            )
            st.plotly_chart(fig_mrp_coverage, use_container_width=True)

        # رسم بياني لتوزيع المكونات حسب نوع الطلب
        fig_order_type = px.pie(
            filtered_analysis, 
            names="Component Order Type", 
            title="توزيع المكونات حسب نوع الطلب",
            color="Component Order Type"
        )
        st.plotly_chart(fig_order_type, use_container_width=True)

        # -------------------------------
        # جدول الكميات الشهرية + الرسم البياني
        # -------------------------------
        if date_cols:
            orders_summary = plan_df.melt(
                id_vars=[col("material"), col("material_desc"), col("order_type")], 
                value_vars=date_cols,
                var_name="Month", 
                value_name="Quantity"
            )
            orders_summary["Month"] = pd.to_datetime(orders_summary["Month"]).dt.month_name()
            orders_grouped = orders_summary.groupby(["Month", col("order_type")]).agg({"Quantity": "sum"}).reset_index()
            pivot_df = orders_grouped.pivot_table(index="Month", columns=col("order_type"), values="Quantity", aggfunc="sum", fill_value=0).reset_index()
            
            if "E" not in pivot_df.columns: pivot_df["E"] = 0
            if "L" not in pivot_df.columns: pivot_df["L"] = 0

            pivot_df["الإجمالي"] = pivot_df["E"] + pivot_df["L"]
            total_sum = pivot_df["الإجمالي"].sum()
            if total_sum > 0:
                pivot_df["E%"] = ((pivot_df["E"] / pivot_df["الإجمالي"]) * 100).round(1).astype(str) + "%"
                pivot_df["L%"] = ((pivot_df["L"] / pivot_df["الإجمالي"]) * 100).round(1).astype(str) + "%"
            else:
                 pivot_df["E%"], pivot_df["L%"] = "0.0%", "0.0%"

            month_order = {m: i for i, m in enumerate(calendar.month_name) if m}
            pivot_df = pivot_df.sort_values(by="Month", key=lambda x: x.map(month_order))

            st.subheader("📊 توزيع الكميات الشهرية حسب نوع الأمر")
            html_table = "<table border='1' style='border-collapse: collapse; width:100%; text-align:center; color:green;'>"
            html_table += "<tr style='background-color:#4CAF50; color:white;'><th>الشهر</th><th>E</th><th>L</th><th>الإجمالي</th><th>E%</th><th>L%</th></tr>"
            for _, row in pivot_df.iterrows():
                html_table += "<tr>"
                html_table += f"<td style='color:blue; font-weight:bold;'>{row['Month']}</td><td>{int(row.get('E', 0))}</td><td>{int(row.get('L', 0))}</td><td>{int(row.get('الإجمالي', 0))}</td><td>{row.get('E%', '')}</td><td>{row.get('L%', '')}</td>"
                html_table += "</tr>"
            html_table += "</table>"
            st.markdown(f"<div style='direction:rtl;'>{html_table}</div>", unsafe_allow_html=True)

            # تحسين الرسم البياني بإضافة تسميات عربية
            fig = px.bar(
                pivot_df, 
                x="Month", 
                y=["E", "L"], 
                barmode="group", 
                text_auto=True, 
                title="رسم بياني لتوزيع الكميات",
                labels={"value": "الكمية", "variable": "نوع الأمر", "Month": "الشهر"},
                template="streamlit"
            )
            st.plotly_chart(fig, use_container_width=True)
            st.markdown("---")

        # -------------------------------
        # تحويل رؤوس الأعمدة التي تحتوي على تواريخ إلى صيغة مختصرة "يوم شهر"
        # -------------------------------
        plan_df.columns = [
            col.strftime("%d %b") if isinstance(col, (datetime.datetime, pd.Timestamp)) else col
            for col in plan_df.columns
        ]

        # -------------------------------
        # زر إنشاء النسخة المضغوطة
        # -------------------------------
        if st.button("🗜️ اضغط هنا لإنشاء النسخة المضغوطة"):
            current_date = datetime.datetime.now().strftime("%d_%b_%Y")

            excel_buffer = BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                plan_df.to_excel(writer, sheet_name="Plan", index=False)
                pivot_by_date.to_excel(writer, sheet_name="Need_By_Date", index=False)
                pivot_by_order.to_excel(writer, sheet_name="Need_By_Order Type", index=False)
                component_analysis.to_excel(writer, sheet_name="Stock_Coverage_Analysis", index=False)
                component_bom_pivot.reset_index().to_excel(writer, sheet_name="Component_in_BOMs", index=False)
                component_df.to_excel(writer, sheet_name="Component", index=False)
                if not mrp_df.empty:
                    mrp_df.to_excel(writer, sheet_name="MRP Contor", index=False)
            excel_buffer.seek(0)

            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zipf:
                zipf.writestr(f"All_Component_Results_{current_date}.xlsx", excel_buffer.getvalue())
            zip_buffer.seek(0)

            st.subheader("🔥 تحميل النسخة الكاملة مضغوطة")
            st.download_button(
                label=" 📊 تحميل الملف المضغوط",
                data=zip_buffer,
                file_name=f"All_Component_Results_{current_date}.zip",
                mime="application/zip"
            )

            st.success("✅ تم إنشاء النسخة المضغوطة بنجاح، وجميع الشيتات موجودة داخل Excel")

# --- التذييل ---
st.markdown(
    """
    <hr>
    <div style="text-align:center; direction:rtl; font-size:14px; color:gray;">
        ✨ تم التنفيذ بواسطة <b>م / رضا رشدي</b> – جميع الحقوق محفوظة © 2025 ✨
    </div>
    """,
    unsafe_allow_html=True
)


