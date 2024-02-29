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


def main():
   
    
    st.set_page_config(
    page_title="Escoles",
    page_icon="🧊"
    )
    
    st.markdown('''
        <style>
        .stApp [data-testid="stToolbar"]{
            display:none;
        }
        </style>
        ''', unsafe_allow_html=True)
        
    st.markdown("""
        # Benvingut a Escola Finder 2024/2025 🏫

        Aquesta aplicació t'ajudarà a decidir amb dades la teva llista de preferències per escollir escola. Utilitzem dades obertes proporcionades per: 🔗 [Portal de Transparència de Catalunya](https://analisi.transparenciacatalunya.cat/)

        Amb aquesta eina, podràs explorar informació sobre l'històric de les preinscripcions en les escoles.""", unsafe_allow_html=True)

    
    button(username="marqitus", floating=True, width=221)
     
    url = "https://analisi.transparenciacatalunya.cat/resource/99md-r3rq.csv"
    df = fetch_data(url)
    
    url2 = "https://analisi.transparenciacatalunya.cat/resource/kvmv-ahh4.csv"
    escoles_raw = fetch_data(url2)
    
  
    df['codi_centre'] = df['codi_centre'].astype(str)
    escoles_raw['codi_centre'] = escoles_raw['codi_centre'].astype(str)
    escoles_raw['any'] = escoles_raw['any'].astype(str)
    
    escoles = escoles_raw[escoles_raw['any'] == '2023']

    df.rename(columns={
        'coordenades_geo_x': 'coordenades_geo_x_2',
        'coordenades_geo_y': 'coordenades_geo_y_2'
    }, inplace=True)
    
    df = pd.merge(df, escoles[['codi_centre', 'adre_a', 'tel_fon', 'e_mail_centre', 'url', 'coordenades_geo_x', 'coordenades_geo_y']],
                     on='codi_centre', how='left')
    df['coordenades_geo_x'].fillna(value=0, inplace=True)  # Replace 0 with a more sensible default if available
    df['coordenades_geo_y'].fillna(value=0, inplace=True)  # Replace 0 with a more sensible default if available
    df['url'] = df['url'].fillna('')
    df['tel_fon'] = df['tel_fon'].fillna('')
    df['adre_a'] = df['adre_a'].fillna('')
    df['e_mail_centre'] = df['adre_a'].fillna('')
    df['codi_centre'] = df['adre_a'].fillna('')
    
    

    if not df.empty:
        # Create a new column that combines school name and municipality
        df['school_with_municipality'] = df['denominaci_completa'] + ' (' + df['nom_municipi'] + ')'
        
        # Use the new combined column for the school search selector
        school_options = df['school_with_municipality'].unique()
        selected_school_with_municipality = st.selectbox('Filtra una escola:', options=school_options)

        # Split the selection to get the school name and municipality
        selected_school, selected_municipality = selected_school_with_municipality.rsplit(' (', 1)
        selected_municipality = selected_municipality.rstrip(')')  # Remove the closing parenthesis

        # Filter the dataframe based on the selected school name and municipality
        filtered_df = df[(df['denominaci_completa'] == selected_school) & (df['nom_municipi'] == selected_municipality)]
        filtered_df['address'] = filtered_df['nom_municipi'] + ', ' + filtered_df['nom_comarca']  # Replace 'additional_address_info' with the actual column name

        if not filtered_df.empty:
            school_info = filtered_df.iloc[0]  # Assuming each school name is unique
            school_lat = school_info['coordenades_geo_y']
            school_lon = school_info['coordenades_geo_x']

            # More code for displaying school information...

            # Now let's handle the map
            st.subheader("Situació de les escoles del municipi:")

            # Get the DataFrame for nearby schools by excluding the selected school
            nearby_schools_df = df[df['nom_municipi'] == selected_municipality]
            nearby_schools_df['address'] = nearby_schools_df['nom_municipi'] + ', ' + nearby_schools_df['nom_comarca']  # Replace 'additional_address_info' with the actual column name
            nearby_schools_df = nearby_schools_df.dropna(subset=['coordenades_geo_x', 'coordenades_geo_y'])
            nearby_schools_df = nearby_schools_df
            nearby_schools_df = nearby_schools_df[(nearby_schools_df['denominaci_completa'] != selected_school) & (nearby_schools_df['nom_municipi'] == selected_municipality)]


            # Create a layer for nearby schools
            nearby_schools_layer = pdk.Layer(
                "ScatterplotLayer",
                data=nearby_schools_df[['coordenades_geo_x', 'coordenades_geo_y', 'denominaci_completa', 'codi_centre', 'nom_naturalesa', 'address', 'nom_municipi','adre_a','tel_fon','e_mail_centre','url']].rename(columns={'coordenades_geo_x': 'lon', 'coordenades_geo_y': 'lat'}),
                get_position='[lon, lat]',
                get_color='[169, 169, 169, 160]',  # Dark gray color for nearby schools
                get_radius=50,
                pickable=True
            )
            
            
            # Create a layer for the selected school
            selected_school_layer = pdk.Layer(
                "ScatterplotLayer",
                data=filtered_df[['coordenades_geo_x', 'coordenades_geo_y', 'denominaci_completa', 'codi_centre', 'nom_naturalesa', 'address', 'nom_municipi','adre_a','tel_fon','e_mail_centre','url']].rename(columns={'coordenades_geo_x': 'lon', 'coordenades_geo_y': 'lat'}),
                get_position='[lon, lat]',
                get_color='[255, 0, 0, 160]',  # Red color for the selected school
                get_radius=50,
                pickable=True
            )

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

            # Define the pydeck chart with both layers
            st.pydeck_chart(pdk.Deck(
                map_style='mapbox://styles/mapbox/light-v9',
                initial_view_state=pdk.ViewState(
                    latitude=school_lat,
                    longitude=school_lon,
                    zoom=15,
                    pitch=0,
                ),
                layers=[nearby_schools_layer,selected_school_layer],  # Add both layers here
                tooltip=tooltip
            ))
                
            st.subheader("Evolució en les preinscripcions:")

            for ense in filtered_df['nom_ensenyament'].unique():
                # Filter by education type and find the minimum 'nivell' for this education type
                min_nivell_per_ense = filtered_df.groupby('nom_ensenyament')['nivell'].transform(min)
                min_nivell_df = filtered_df[filtered_df['nivell'] == min_nivell_per_ense]
                min_nivell_df = min_nivell_df.sort_values(by='curs', ascending=True)


                fig = go.Figure()

                # Iterate over unique 'curs' values within this filtered dataset
                for curs in min_nivell_df['curs'].unique():
                    curs_df = min_nivell_df[min_nivell_df['curs'] == curs]

                    # Aggregate data if necessary, or ensure curs_df is correctly filtered for this visualization
                    # Add initial seat offerings, 1st choice assignments, and other assignments as different traces
                    fig.add_trace(go.Bar(
                        x=curs_df ['curs'],  # 'curs' as X-axis
                        y=curs_df['oferta_inicial_places'],  # Sum or average if multiple rows
                        name='Initial Seat Offerings',
                        marker_color='lightgray',
                        hovertemplate='<b>Year:</b> %{x}<br><b>Oferta de places:</b> %{y}<extra></extra>'  # Custom hover label

                    ))

                    fig.add_trace(go.Bar(
                        x=curs_df ['curs'],
                        y=curs_df['assignacions_1a_peticio'],
                        base=0,
                        name='1st Choice Assignments',
                        marker_color='blue',
                        width=0.2,
                        hovertemplate='<b>Year:</b> %{x}<br><b>1a opció:</b> %{y}<extra></extra>'  # Custom hover label
                        
                    ))

                    fig.add_trace(go.Bar(
                        x=curs_df['curs'],
                        y=curs_df['assignacions_altres_peticions'],
                        base=curs_df['assignacions_1a_peticio'],
                        name='Other Assignments',
                        marker_color='rgba(135, 206, 250, 0.6)',
                        width=0.2,
                        hovertemplate='<b>Year:</b> %{x}<br><b>Altres peticions:</b> %{y}<extra></extra>'  # Custom hover label
                    ))

                # Update the layout for the figure
                fig.update_layout(
                    autosize=True,
                    barmode='overlay',
                    xaxis=dict(type='category', title="Curs"),
                    yaxis=dict(title=""),
                    title_text=f"{ense} ",
                    # Disable zoom and other interactive capabilities
                    dragmode=False,
                    showlegend=False,
                )

                # Display the figure with disabled Plotly menu and static plot configuration
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
                
                
            
            st.subheader("Inscripcions pels cursos o nivells:")
            
            st.markdown("""En aquesta visualització es poden veure les inscripcions de l'escola en tots els cursos, no només en els primers cursos de cada etapa educativa.""", unsafe_allow_html=True)
            
            # Selector for unique "Curs" values
            unique_curs = filtered_df['curs'].unique()
            selected_curs = st.selectbox('Selecciona un curs escolar:', options=unique_curs)
            
            for ense in filtered_df['nom_ensenyament'].unique():
                ense_df = filtered_df[filtered_df['nom_ensenyament'] == ense]
                ense_df = filtered_df[filtered_df['curs'] == selected_curs]
                ense_df = ense_df.sort_values(by='nivell', ascending=True)

                fig = go.Figure()

                # Add oferta_inicial_places as the range indicator in light gray
                fig.add_trace(go.Bar(
                    x=ense_df['nivell'],
                    y=ense_df['oferta_inicial_places'],
                    name='Initial Seat Offerings',
                    marker_color='lightgray',
                    width=0.4,
                    hovertemplate='<b>Year:</b> %{x}<br><b>Oferta de places:</b> %{y}<extra></extra>'
                ))

                # Add bars for assignments, ensuring they start from 0
                fig.add_trace(go.Bar(
                    x=ense_df['nivell'],
                    y=ense_df['assignacions_1a_peticio'],
                    base=0,
                    name='1st Choice Assignments',
                    marker_color='blue',
                    width=0.2,
                    hovertemplate='<b>Year:</b> %{x}<br><b>1a opció:</b> %{y}<extra></extra>'
                ))

                fig.add_trace(go.Bar(
                    x=ense_df['nivell'],
                    y=ense_df['assignacions_altres_peticions'],
                    base=ense_df['assignacions_1a_peticio'],
                    name='Other Assignments',
                    marker_color='rgba(135, 206, 250, 0.6)',
                    width=0.2,
                    hovertemplate='<b>Year:</b> %{x}<br><b>Altres peticions:</b> %{y}<extra></extra>'
                ))
                

                # Update the layout for the figure
                fig.update_layout(
                    autosize=True,
                    barmode='overlay',  # Allows the gray range bars to act as background
                    xaxis=dict(type='category', title="Nivell", tickmode='array', tickvals=ense_df['nivell'].unique()),
                    yaxis=dict(title=""),
                    title_text=f"{ense}",
                    showlegend=False,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )


                # Display the figure with disabled Plotly menu and static plot configuration
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

            st.subheader("Escoles del municipi:")
            st.markdown("""En aquesta taula podreu veure les escoles del municipi a la seleccionada.""", unsafe_allow_html=True)
            nivell_options = sorted(nearby_schools_df['nivell'].unique())
            selected_nivell = st.selectbox('Selecciona un curs:', options=nivell_options, index=0)  # 'index=0' starts the selection at the first option
            nearby_schools_df = nearby_schools_df[nearby_schools_df['nivell'] == selected_nivell]
            st.dataframe(nearby_schools_df[['denominaci_completa', 'nom_naturalesa', 'nom_ensenyament','nivell','oferta_inicial_grups','oferta_inicial_places','assignacions']])

            
            
    else:
        st.error("Failed to fetch data.")

if __name__ == "__main__":
    main()
