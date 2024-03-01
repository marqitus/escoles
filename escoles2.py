import streamlit as st
import pandas as pd
import requests
from io import StringIO
import pydeck as pdk
import plotly.express as px
import plotly.graph_objects as go
from streamlit_extras.buy_me_a_coffee import button 

# Define the fetch_data function with st.cache_data for caching
@st.cache_data



def fetch_data(url, limit=1000):
    offset = 0
    all_data = pd.DataFrame()

    while True:
        # Correctly build the URL with limit and offset
        paginated_url = f"{url}?$limit={limit}&$offset={offset}"
        response = requests.get(paginated_url)

        if response.status_code == 200:
            # Use StringIO to convert the text data into a DataFrame
            data = pd.read_csv(StringIO(response.text))
            
            # If no data is returned, we've reached the end of the dataset
            if data.empty:
                break
            
            # Concatenate the fetched data with the existing DataFrame
            all_data = pd.concat([all_data, data], ignore_index=True)
            
            # Increase the offset for the next iteration
            offset += limit
        else:
            print(f"Failed to fetch data: {response.status_code}")
            break

    return all_data

def preprocess_school_data(df, escoles_raw):
    # Ensure 'codi_centre' and 'any' are of string type in both DataFrames
    df['codi_centre'] = df['codi_centre'].astype(str)
    escoles_raw['codi_centre'] = escoles_raw['codi_centre'].astype(str)
    escoles_raw['any'] = escoles_raw['any'].astype(str)
    
    # Filter the escoles_raw DataFrame for rows where 'any' is '2023'
    escoles = escoles_raw[escoles_raw['any'] == '2023']

    # Rename columns in df to avoid name clashes during merge
    df.rename(columns={
        'coordenades_geo_x': 'coordenades_geo_x_2',
        'coordenades_geo_y': 'coordenades_geo_y_2'
    }, inplace=True)
    
    # Merge df with escoles on 'codi_centre', keeping all rows from df and adding matching rows from escoles
    df = pd.merge(df, escoles[['codi_centre', 'adre_a', 'tel_fon', 'e_mail_centre', 'url', 'coordenades_geo_x', 'coordenades_geo_y']],
                  on='codi_centre', how='left')
    
    # Fill missing values for specific columns
    df['coordenades_geo_x'].fillna(value=0, inplace=True)  # Replace 0 with a more sensible default if available
    df['coordenades_geo_y'].fillna(value=0, inplace=True)  # Replace 0 with a more sensible default if available
    df['url'] = df['url'].fillna('')
    df['tel_fon'] = df['tel_fon'].fillna('')
    df['adre_a'] = df['adre_a'].fillna('')
    df['e_mail_centre'] = df['adre_a'].fillna('')
    df['codi_centre'] = df['adre_a'].fillna('')
        
    df['school_with_municipality'] = df['denominaci_completa'] + ' (' + df['nom_municipi'] + ')'
    df['address'] = df['nom_municipi'] + ', ' + df['nom_comarca']  # Replace 'additional_address_info' with the actual column name
    
    return df


def setup_page():
    # Set page configuration
    st.set_page_config(
        page_title="Busca-escola 2024/2025",
        page_icon="🏫"
    )
    
    # Hide Streamlit's default toolbar
    st.markdown('''
        <style>
        .stApp [data-testid="stToolbar"]{
            display:none;
        }
        </style>
        ''', unsafe_allow_html=True)
        
    # Display introductory markdown
    st.markdown("""
        # 🏫 Busca-escola 2024/2025 

        Benvinguts a **Busca-escola**. Aquesta aplicació està dissenyada per **ajudar-vos a prendre decisions informades** quan esteu configurant la vostra llista de preferències per a l'elecció d'escoles. Gràcies a l'ús de **dades obertes proporcionades pel [Portal de Transparència de Catalunya](https://analisi.transparenciacatalunya.cat/)**, podeu:
        - **Explorar dades detallades** sobre les preinscripcions històriques en diferents escoles.
        - **Comparar preinscripcions** entre escoles, incloent l'oferta de places i les assignacions.
        
        La Preinscripció serà telemàtica a la [web de preinscripció](https://preinscripcio.gencat.cat/ca/inici/)
        . També podeu trobar tota la informació sobre la preinscripció a la web del [Consorci d’educació.](https://www.edubcn.cat/ca/alumnat_i_familia/informacio_general_matriculacio/preinscripcio_info).
        - **INFANTIL i PRIMÀRIA**: El període de preinscripció serà del **6 al 20 de març de 2024**.
        - **SECUNDÀRIA**: El període de preinscripció serà del **8 al 20 de març de 2024**.
        
        """, unsafe_allow_html=True)

    # Example of a custom button call; ensure this function is defined or imported in your script
    button(username="marqitus", floating=False, width=221)

def get_nearby_schools_df(df, selected_municipality, selected_school):
    nearby_schools_df = df[df['nom_municipi'] == selected_municipality]
    nearby_schools_df['address'] = nearby_schools_df['nom_municipi'] + ', ' + nearby_schools_df['nom_comarca']
    nearby_schools_df = nearby_schools_df.dropna(subset=['coordenades_geo_x', 'coordenades_geo_y'])
    nearby_schools_df = nearby_schools_df[(nearby_schools_df['denominaci_completa'] != selected_school) & (nearby_schools_df['nom_municipi'] == selected_municipality)]
    return nearby_schools_df

def create_pydeck_layer(df, color):
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df[['coordenades_geo_x', 'coordenades_geo_y', 'denominaci_completa', 'codi_centre', 'nom_naturalesa', 'address', 'nom_municipi','adre_a','tel_fon','e_mail_centre','url']].rename(columns={'coordenades_geo_x': 'lon', 'coordenades_geo_y': 'lat'}),
        get_position='[lon, lat]',
        get_color=color,
        get_radius=50,
        pickable=True
    )
    return layer

def plot_pre_registration_evolution(filtered_df):
    
    for ense in filtered_df['nom_ensenyament'].unique():
        min_nivell_per_ense = filtered_df.groupby('nom_ensenyament')['nivell'].transform(min)
        min_nivell_df = filtered_df[filtered_df['nivell'] == min_nivell_per_ense]
        min_nivell_df = min_nivell_df.sort_values(by='curs', ascending=True)

        fig = go.Figure()

        for curs in min_nivell_df['curs'].unique():
            curs_df = min_nivell_df[min_nivell_df['curs'] == curs]

            fig.add_trace(go.Bar(
                x=curs_df['curs'],
                y=curs_df['oferta_inicial_places'],
                name='Initial Seat Offerings',
                marker_color='lightgray'
            ))

            fig.add_trace(go.Bar(
                x=curs_df['curs'],
                y=curs_df['assignacions_1a_peticio'],
                base=0,
                name='1st Choice Assignments',
                marker_color='blue',
                width=0.2
            ))

            fig.add_trace(go.Bar(
                x=curs_df['curs'],
                y=curs_df['assignacions_altres_peticions'],
                base=curs_df['assignacions_1a_peticio'],
                name='Other Assignments',
                marker_color='rgba(135, 206, 250, 0.6)',
                width=0.2
            ))

        fig.update_layout(
            autosize=True,
            barmode='overlay',
            xaxis=dict(type='category', title="Curs"),
            yaxis=dict(title=""),
            title_text=f"{ense}",
            dragmode=False,
            showlegend=False,
        )

        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

def display_school_map(df, selected_municipality, selected_school, school_info):
    """
    Display a map with layers for nearby schools and the selected school.

    Args:
    - df: The full DataFrame containing schools data.
    - selected_municipality: The municipality selected by the user.
    - selected_school: The school selected by the user.
    - school_info: A dict or similar object containing 'coordenades_geo_x' and 'coordenades_geo_y' for the selected school.
    """
    # Extract school's latitude and longitude from school_info
    school_lat = school_info['coordenades_geo_y']
    school_lon = school_info['coordenades_geo_x']
    
    # Generate DataFrame for nearby schools
    nearby_schools_df = get_nearby_schools_df(df, selected_municipality, selected_school)
    
    # Create a layer for nearby schools
    nearby_schools_layer = create_pydeck_layer(nearby_schools_df, '[169, 169, 169, 160]')  # Dark gray color
    
    # Filter DataFrame for the selected school
    filtered_df = df[df['denominaci_completa'] == selected_school]
    
    # Create a layer for the selected school
    selected_school_layer = create_pydeck_layer(filtered_df, '[255, 0, 0, 160]')  # Red color
    
    # Define the tooltip for interactivity
    tooltip = {
        "html": "<b>Nom:</b> {denominaci_completa}<br/>" +
                "<b>Codi</b> {codi_centre}<br/>" +
                "<b>Naturalesa:</b> {nom_naturalesa}<br/>" +
                "<b>Adreça:</b> {adre_a}<br/>" +
                "<b>Municipi:</b> {address}<br/>" +
                "<b>Telèfon:</b> {tel_fon}<br/>"+
                "<b>Correu electrònic:</b> {e_mail_centre}<br/>"+
                "<b>Web:</b> {url}", 
        "style": {
            "backgroundColor": "steelblue",
            "color": "white"
        }
    }

    # Display the map
    st.pydeck_chart(pdk.Deck(
        map_style='mapbox://styles/mapbox/light-v9',
        initial_view_state=pdk.ViewState(
            latitude=school_lat,
            longitude=school_lon,
            zoom=15,
            pitch=0,
        ),
        layers=[nearby_schools_layer, selected_school_layer],
        tooltip=tooltip
    ))
    
def plot_inscriptions_by_curs(filtered_df):
    """
    Plot inscriptions for courses or levels within a selected school year.
    
    Args:
    - filtered_df: DataFrame containing the filtered school data.
    """
    # Selector for unique "Curs" values
    unique_curs = filtered_df['curs'].unique()
    selected_curs = st.selectbox('Selecciona un curs escolar:', options=unique_curs)
    
    for ense in filtered_df['nom_ensenyament'].unique():
        ense_df = filtered_df[(filtered_df['nom_ensenyament'] == ense) & (filtered_df['curs'] == selected_curs)]
        ense_df = ense_df.sort_values(by='nivell', ascending=True)

        fig = go.Figure()

        # Iterate through each "nivell" and plot its data
        for nivell in ense_df['nivell'].unique():
            nivell_df = ense_df[ense_df['nivell'] == nivell]
            
            # Initial Seat Offerings
            fig.add_trace(go.Bar(
                x=[nivell],
                y=nivell_df['oferta_inicial_places'],
                name='Initial Seat Offerings',
                marker_color='lightgray',
                width=0.4,
                hovertemplate='<b>Nivell:</b> %{x}<br><b>Oferta de places:</b> %{y}<extra></extra>'
            ))

            # 1st Choice Assignments
            fig.add_trace(go.Bar(
                x=[nivell],
                y=nivell_df['assignacions_1a_peticio'],
                base=0,
                name='1st Choice Assignments',
                marker_color='blue',
                width=0.2,
                hovertemplate='<b>Nivell:</b> %{x}<br><b>1a opció:</b> %{y}<extra></extra>'
            ))

            # Other Assignments
            fig.add_trace(go.Bar(
                x=[nivell],
                y=nivell_df['assignacions_altres_peticions'],
                base=nivell_df['assignacions_1a_peticio'],
                name='Other Assignments',
                marker_color='rgba(135, 206, 250, 0.6)',
                width=0.2,
                hovertemplate='<b>Nivell:</b> %{x}<br><b>Altres peticions:</b> %{y}<extra></extra>'
            ))

        # Update the layout for the figure
        fig.update_layout(
            autosize=True,
            barmode='overlay',  # Allows the gray range bars to act as background
            xaxis=dict(type='category', title="Nivell"),
            yaxis=dict(title="Places"),
            title_text=f"Inscripcions per {ense} en {selected_curs}",
            showlegend=False,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        # Display the figure with disabled Plotly menu and static plot configuration
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

def plot_data_across_schools(filtered_df):
    """
    Plot a column graph comparing specific metrics across selected schools.

    Args:
    - filtered_df: DataFrame containing data for the selected schools.
    """
    # Check if the DataFrame is not empty
    if not filtered_df.empty:
      
        fig = go.Figure()

        # Main measure - "oferta_inicial_places", now plotted on the x-axis for a horizontal bar
        fig.add_trace(go.Bar(
            y=filtered_df['school_with_municipality'],  # This now sets the categories on the y-axis
            x=filtered_df['oferta_inicial_places'],  # Values on the x-axis
            orientation='h',  # Specify the bar orientation as horizontal
            name='Initial Seat Offerings',
            marker_color='lightgray',
        ))

        # Comparative measure 1 - "assignacions_1a_peticio"
        fig.add_trace(go.Bar(
            y=filtered_df['school_with_municipality'],
            x=filtered_df['assignacions_1a_peticio'],
            name='1st Choice Assignments',
            base=0,
            marker_color='blue',
            orientation='h',  # Horizontal orientation
            width=0.2,  # Adjust width to control the bar thickness
        ))

        # Comparative measure 2 - "assignacions_altres_peticions"
        fig.add_trace(go.Bar(
            y=filtered_df['school_with_municipality'],
            x=filtered_df['assignacions_altres_peticions'],
            orientation='h',  # Horizontal orientation
            base=filtered_df['assignacions_1a_peticio'],
            marker_color='rgba(135, 206, 250, 0.6)',
            name='Other Assignments',
            width=0.2,  # Adjust width to control the bar thickness
        ))

        # Update layout for clarity, adjusting axis titles for the horizontal orientation
        fig.update_layout(
            title='',
            yaxis_title="",
            xaxis_title="",
            legend_title="Metric",
            barmode='overlay',  # Overlaid bars to approximate a bullet chart
            showlegend=False,  # Hide legend if not needed
        )

        # Display the figure in the Streamlit app
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        
    else:
        st.write("No data available to plot.")


def main():
   
    
    setup_page()
     
    url = "https://analisi.transparenciacatalunya.cat/resource/99md-r3rq.csv"
    url2 = "https://analisi.transparenciacatalunya.cat/resource/kvmv-ahh4.csv"
   
    df = fetch_data(url)
    escoles_raw = fetch_data(url2)
 
    df=preprocess_school_data(df, escoles_raw)
    
    
    if not df.empty:
        tab1, tab2 = st.tabs(["Busca una escola", "Compara escoles"])

        with tab1:
     
            # Use the new combined column for the school search selector
            school_options = df['school_with_municipality'].unique()
            selected_school_with_municipality = st.selectbox('Filtra una escola:', options=school_options)

            # Split the selection to get the school name and municipality
            selected_school, selected_municipality = selected_school_with_municipality.rsplit(' (', 1)
            selected_municipality = selected_municipality.rstrip(')')  # Remove the closing parenthesis

            # Filter the dataframe based on the selected school name and municipality
            filtered_df = df[(df['denominaci_completa'] == selected_school) & (df['nom_municipi'] == selected_municipality)]
     
            if not filtered_df.empty:
                school_info = filtered_df.iloc[0]  # Assuming each school name is unique

                #################
                st.subheader("Situació de les escoles del municipi:")
                st.markdown("""Mapa amb <span style="color:red">**l'escola seleccionada**&nbsp;</span> i les **escoles del municipi.**""", unsafe_allow_html=True)
         
                display_school_map(df, selected_municipality, selected_school, school_info)

                #################
                st.subheader("Evolució en les preinscripcions:")
                st.markdown("""En aquesta visualització es poden veure les inscripcions de l'escola en el curs s'entrada en els diferents anys. (
                <span style="color:lightgray">**Oferta de places**&nbsp;</span>
                <span style="color:blue">**1a opció**&nbsp;</span>
                <span style="color:rgba(135, 206, 250, 0.6)">**Assignació posterior**</span>
                )""", unsafe_allow_html=True)
                plot_pre_registration_evolution(filtered_df)
                
                #################
                st.subheader("Inscripcions pels cursos o nivells:")
                st.markdown("""En aquesta visualització es poden veure les inscripcions de l'escola en tots els cursos, no només en els primers cursos de cada etapa educativa.""", unsafe_allow_html=True)
                plot_inscriptions_by_curs(filtered_df)
                 

        with tab2:

            # Assuming 'school_with_municipality' is a combined column you've created
            all_options = df['school_with_municipality'].unique()
            selected_options = st.multiselect('Selecciona escoles:', options=all_options, default=all_options[:1])

            # Further processing based on selected_options
            # Splitting the selections into schools and municipalities, then filtering the DataFrame accordingly
            selected_schools, selected_municipalities = zip(*[option.rsplit(' (', 1) for option in selected_options])
            selected_municipalities = [muni.rstrip(')') for muni in selected_municipalities]

            # Initial filtering based on the selected schools and municipalities
            filtered_multi_df = df[df['school_with_municipality'].isin(selected_options)]
            
            # Selector for educational program types (nom_ensenyament)
            unique_ense = filtered_multi_df['nom_ensenyament'].unique()
            selected_ense = st.selectbox('Selecciona un tipus d’ensenyament:', options=unique_ense, key='unique_ense_key')
            # Selector for "curs" (year/course)
            unique_curs = filtered_multi_df['curs'].unique()

            # Selector for "nivell" (level)
            unique_nivell = sorted(filtered_multi_df['nivell'].unique())
            
            col1, col2 = st.columns(2)

            with col1:
                selected_curs = st.selectbox('Selecciona un curs escolar:', options=unique_curs, index=0, key='unique_curs_key')

            with col2:
                selected_nivell = st.selectbox('Selecciona un nivell:', options=unique_nivell, index=0, key='unique_nivell_key')
                  
            # Further filtering based on selected educational program
            filtered_multi_df = filtered_multi_df[filtered_multi_df['nom_ensenyament'] == selected_ense]
            # Further filtering based on selected "curs"
            filtered_multi_df = filtered_multi_df[filtered_multi_df['curs'] == selected_curs]
            # Final filtering based on selected "nivell"
            filtered_multi_df = filtered_multi_df[filtered_multi_df['nivell'] == selected_nivell]


            if not filtered_multi_df.empty:
                
                st.subheader('Comparativa de places entre escoles:')
                
                st.markdown("""Inscripcions de les escoles seleccionades en el curs i nivell seleccionats. (
                <span style="color:lightgray">**Oferta de places**&nbsp;</span>
                <span style="color:blue">**1a opció**&nbsp;</span>
                <span style="color:rgba(135, 206, 250, 0.6)">**Assignació posterior**</span>
                )""", unsafe_allow_html=True)
                
                plot_data_across_schools(filtered_multi_df)

            else:
                st.write("No data available for the selected schools/municipalities.")
    else:
        st.error("Failed to fetch data.")

if __name__ == "__main__":
    main()
    

        
