import streamlit as st
import pandas as pd
from app.sanmar_automation import SanMarAutomation

# Configure page
st.set_page_config(
    page_title="SanMar Product Automation",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize automation
def init_automation():
    return SanMarAutomation()

# Main title
st.title("🤖 SanMar Product Automation")
st.markdown("Run automated inventory checks on SanMar products")

# Sidebar for controls
with st.sidebar:
    st.header("SanMar Automation")
    
    # Login credentials
    with st.expander("🔐 Login Credentials", expanded=True):
        username = st.text_input("Username:", value="mikehorton")
        password = st.text_input("Password:", value="6432Order", type="password")
    
    # Category search
    category_query = st.text_input(
        "Category to search:",
        placeholder="e.g., polo, t-shirt, jacket",
        help="Enter category name to search and check inventory"
    )
    
    # Automation button
    automation_button = st.button("🤖 Run Full Automation", type="primary", use_container_width=True)

# Main content area
if automation_button and category_query and username and password:
    # Initialize automation
    automation = init_automation()
    
    # Run the full automation
    results = automation.run_full_automation(username, password, category_query)
    
    if results:
        st.success(f"✅ Automation completed! Found inventory data for {len(results)} products")
        
        # Display results in tabs
        tab1, tab2, tab3 = st.tabs(["📊 Summary", "📋 Detailed View", "📥 Export Data"])
        
        with tab1:
            # Summary statistics
            col1, col2, col3, col4 = st.columns(4)
            
            total_products = len(results)
            total_variants = sum(len(r.get('variants', [])) for r in results)
            total_stock = sum(r.get('total_stock', 0) for r in results)
            in_stock_products = sum(1 for r in results if r.get('total_stock', 0) > 0)
            
            with col1:
                st.metric("Total Products", total_products)
            with col2:
                st.metric("Total Variants", total_variants)
            with col3:
                st.metric("Total Stock", total_stock)
            with col4:
                st.metric("In Stock", in_stock_products)
            
            # Stock distribution chart
            if results:
                stock_data = [r.get('total_stock', 0) for r in results]
                product_names = [r.get('product_name', r.get('name', 'Unknown'))[:30] + "..." 
                               if len(r.get('product_name', r.get('name', 'Unknown'))) > 30 
                               else r.get('product_name', r.get('name', 'Unknown')) 
                               for r in results]
                
                df_chart = pd.DataFrame({
                    'Product': product_names,
                    'Total Stock': stock_data
                })
                
                st.subheader("📈 Stock Levels by Product")
                st.bar_chart(df_chart.set_index('Product'))
        
        with tab2:
            # Detailed view of each product
            st.subheader("📋 Product Inventory Details")
            
            for result in results:
                with st.expander(
                    f"🏷️ {result.get('product_name', result.get('name', 'Unknown'))} "
                    f"(Stock: {result.get('total_stock', 0)})", 
                    expanded=False
                ):
                    col1, col2 = st.columns([1, 1])
                    
                    with col1:
                        st.write(f"**Product Code:** {result.get('product_code', result.get('code', 'N/A'))}")
                        st.write(f"**Base Product:** {result.get('base_product', 'N/A')}")
                        st.write(f"**Total Stock:** {result.get('total_stock', 0)}")
                        st.write(f"**Number of Variants:** {len(result.get('variants', []))}")
                        
                        if result.get('url'):
                            st.write(f"**URL:** {result.get('url', 'N/A')}")
                    
                    with col2:
                        # Variants table
                        if result.get('variants'):
                            variants_df = pd.DataFrame(result['variants'])
                            if not variants_df.empty:
                                st.write("**Variants:**")
                                # Select relevant columns for display
                                display_cols = ['size', 'color', 'stock_level']
                                available_cols = [col for col in display_cols if col in variants_df.columns]
                                if available_cols:
                                    st.dataframe(variants_df[available_cols], use_container_width=True)
        
        with tab3:
            # Export functionality
            st.subheader("📥 Export Data")
            
            # Format data for export
            formatted_results = automation.format_results_for_display(results)
            
            # Create detailed data for crosstab
            detailed_data = []
            
            for result in formatted_results:
                # Detailed rows for each variant
                for variant in result.get('Variants', []):
                    detailed_data.append({
                        'Product Code': result['Product Code'],
                        'Product Name': result['Product Name'],
                        'Base Product': result['Base Product'],
                        'Variant Code': variant['Variant Code'],
                        'Size': variant['Size'],
                        'Color': variant['Color'],
                        'Stock Level': variant['Stock Level'],
                        'URL': result['URL']
                    })
            
            if detailed_data:
                detailed_df = pd.DataFrame(detailed_data)
                
                # Crosstab Format Options
                st.write("**📊 Crosstab Export Options:**")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Format 1: Size × Color Combinations**")
                    
                    # Create a combination column for Size-Color
                    df_copy1 = detailed_df.copy()
                    df_copy1['Size_Color'] = df_copy1['Size'].astype(str) + ' - ' + df_copy1['Color'].astype(str)
                    
                    # Create crosstab with product info as index and size-color combinations as columns
                    crosstab_df1 = df_copy1.pivot_table(
                        index=['Product Code', 'Product Name', 'Base Product', 'URL'],
                        columns='Size_Color',
                        values='Stock Level',
                        fill_value=0,
                        aggfunc='sum'
                    ).reset_index()
                    
                    # Display sample of the crosstab
                    st.dataframe(crosstab_df1.head(3), use_container_width=True)
                    
                    # Download button
                    csv_crosstab1 = crosstab_df1.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Size×Color Crosstab",
                        data=csv_crosstab1,
                        file_name=f"sanmar_crosstab_size_color_{category_query}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                
                with col2:
                    st.write("**Format 2: Sizes as Columns, Products×Colors as Rows**")
                    
                    # Create crosstab with sizes as columns
                    df_copy2 = detailed_df.copy()
                    df_copy2['Product_Color'] = df_copy2['Product Code'] + ' - ' + df_copy2['Color'].astype(str)
                    
                    crosstab_df2 = df_copy2.pivot_table(
                        index=['Product_Color', 'Product Code', 'Product Name', 'Color'],
                        columns='Size',
                        values='Stock Level',
                        fill_value=0,
                        aggfunc='sum'
                    ).reset_index()
                    
                    # Display sample of the crosstab
                    st.dataframe(crosstab_df2.head(3), use_container_width=True)
                    
                    # Download button
                    csv_crosstab2 = crosstab_df2.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Product×Size Crosstab",
                        data=csv_crosstab2,
                        file_name=f"sanmar_crosstab_product_size_{category_query}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                
                # Comprehensive crosstab format (all products in one table)
                st.write("**Format 3: Complete Inventory Matrix**")
                
                # Create the most comprehensive crosstab
                df_copy3 = detailed_df.copy()
                df_copy3['Size_Color'] = df_copy3['Size'].astype(str) + ' (' + df_copy3['Color'].astype(str) + ')'
                
                crosstab_df3 = df_copy3.pivot_table(
                    index=['Product Code', 'Product Name'],
                    columns='Size_Color',
                    values='Stock Level',
                    fill_value=0,
                    aggfunc='sum'
                ).reset_index()
                
                # Add total column
                size_color_cols = [col for col in crosstab_df3.columns if col not in ['Product Code', 'Product Name']]
                crosstab_df3['Total Stock'] = crosstab_df3[size_color_cols].sum(axis=1)
                
                st.dataframe(crosstab_df3, use_container_width=True)
                
                # Download button for comprehensive format
                csv_crosstab3 = crosstab_df3.to_csv(index=False)
                st.download_button(
                    label="📥 Download Complete Inventory Matrix",
                    data=csv_crosstab3,
                    file_name=f"sanmar_inventory_matrix_{category_query}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
                
                # Traditional detailed format (optional)
                with st.expander("📋 Traditional Detailed Format"):
                    st.dataframe(detailed_df, use_container_width=True)
                    
                    # Download button for traditional detailed data
                    csv_detailed = detailed_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Traditional Detailed CSV",
                        data=csv_detailed,
                        file_name=f"sanmar_inventory_detailed_{category_query}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
    
    else:
        st.error("❌ Automation failed. Please check your credentials and try again.")

elif automation_button:
    if not category_query:
        st.error("Please enter a category to search")
    if not username or not password:
        st.error("Please enter your SanMar login credentials")

# Information section
with st.expander("ℹ️ How to use this tool", expanded=False):
    st.markdown("""
    ### 🤖 SanMar Automation
    - Logs into SanMar automatically
    - Searches for products in the specified category
    - Fetches live inventory data for all found products
    - Provides detailed stock levels by size, color, and location
    - Allows export of inventory data to CSV in multiple crosstab formats
    
    **Note:** Automation requires valid SanMar credentials and may take several minutes depending on the number of products found.
    """)

# Footer
st.markdown("---")
st.markdown("*SanMar Product Automation Tool*")
