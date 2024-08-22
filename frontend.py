import requests
from nicegui import ui
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

def fetch_data(vcluster_name):
    response = requests.get(f"http://148.187.151.141:8000/status/{vcluster_name}")
    if response.status_code == 200:
        return response.json()
    else:
        return {}

def fetch_history(vcluster_name):
    response = requests.get(f"http://148.187.151.141:8000/history/{vcluster_name}")
    if response.status_code == 200:
        return response.json()
    else:
        return {}

labels = ['eiger', 'todi']

@ui.page('/')
def main():
    with ui.tabs().classes('w-full') as tabs:
        tab_refs = [ui.tab(e) for e in labels]

    with ui.tab_panels(tabs, value=tab_refs[0]).classes('w-full'):
        for label, tab in zip(labels, tab_refs):
            response = fetch_data(label)
            date = response["datetime"]
            data = response["body"]
            history = fetch_history(label)["body"]
            # make some preparations
            hist_avail = []
            hist_unavail = []
            hist_occupancy = []
            hist_availability = []
            for i in range(history["count"]):
                hist_avail.append(history["num_nodes_allocated"][i] + history["num_nodes_idle"][i])
                hist_unavail.append(history["num_nodes_total"][i] - hist_avail[i])
                hist_availability.append(round(100 * float(hist_avail[i] / history["num_nodes_total"][i]), 2))
                if hist_avail[i]:
                    hist_occupancy.append(round(100 * float(history["num_nodes_allocated"][i] / hist_avail[i]), 2))
                else:
                    hist_occupancy.append(0)

            with ui.tab_panel(tab):
                with ui.column().classes('w-full items-center'):
                    columns = [
                        {'name': 'name', 'field' : 'name', 'label': 'Name', 'required': True, 'align': 'left'},
                        {'name': 'value', 'field' : 'value', 'label': 'Value'}
                    ]
                    num_avail = data["num_nodes_allocated"] + data["num_nodes_idle"]
                    num_unavail = data["num_nodes_total"] - num_avail
                    rows = [
                        {'name': 'Total number of nodes',       'value': data["num_nodes_total"]},
                        {'name': 'Number of available nodes',   'value': num_avail},
                        {'name': 'Node availability (%)',       'value': round(100 * float(num_avail /  data["num_nodes_total"]), 2)},
                        {'name': 'Number of allocate nodes',    'value': data["num_nodes_allocated"]},
                        {'name': 'Number of idle nodes',        'value': data["num_nodes_idle"]},
                        {'name': 'Number of unavailable nodes', 'value': num_unavail},
                        {'name': 'Occupancy of available nodes (%)', 'value': round(100 * float(data["num_nodes_allocated"] / num_avail), 2)},
                        {'name': 'Number of finished jobs in the past 24H', 'value': data["num_finished_jobs"]},
                        {'name': 'Last measurment date and time (UTC)', 'value': date}
                    ]
                    ui.table(columns=columns, rows=rows, row_key='name')
                    categories = ['1','2','3-4','5-8','9-16','17-32','33-64','65-128','129-256','>256']
                    with ui.pyplot():
                        plt.title('Pending jobs')
                        plt.bar(categories, data["pending_jobs"])
                        plt.ylabel('Number of jobs')
                        plt.xlabel('Number of nodes')
                        plt.xticks(rotation=90)
                        plt.subplots_adjust(bottom=0.25)
                        plt.gca().yaxis.set_major_locator(MaxNLocator(min_n_ticks=0, integer=True))

                    with ui.pyplot():
                        plt.title('Running jobs')
                        plt.bar(categories, data["running_jobs"])
                        plt.ylabel('Number of jobs')
                        plt.xlabel('Number of nodes')
                        plt.xticks(rotation=90)
                        plt.subplots_adjust(bottom=0.25)
                        plt.gca().yaxis.set_major_locator(MaxNLocator(min_n_ticks=0, integer=True))

                    with ui.pyplot():
                        plt.title('Node distribution')
                        plt.plot(history["time_shift"], history["num_nodes_total"], 'o-', label='total')
                        plt.plot(history["time_shift"], hist_avail, 'o-', label='available')
                        plt.plot(history["time_shift"], hist_unavail, 'o-', label='unavailable')
                        plt.xlabel('Minutes in the past')
                        plt.ylabel('Node count')
                        plt.ylim(bottom=0)
                        plt.legend()

                    with ui.pyplot():
                        plt.title('Availability and occupancy')
                        plt.plot(history["time_shift"], hist_availability, 'o-', label='node availability')
                        plt.plot(history["time_shift"], hist_occupancy, 'o-', label='occupancy of available nodes')
                        plt.xlabel('Minutes in the past')
                        plt.ylabel('%')
                        plt.ylim(bottom=0)
                        plt.legend()

#        with ui.tab_panel(one):
#            with ui.column().classes('w-full items-center'):
#                columns = [
#                    {'name': 'name', 'field' : 'name', 'label': 'Name', 'required': True, 'align': 'left'},
#                    {'name': 'value', 'field' : 'value', 'label': 'Value'}
#                ]
#                rows = [
#                    {'name': 'Total number of nodes', 'value': data["num_nodes_total"]}
#                ]
#                ui.table(columns=columns, rows=rows, row_key='name')
#    #        with ui.column().classes('w-full items-center'):
#    #            with ui.card().classes('no-shadow border-[1px] w-64 h-32 justify-center items-center'):
#    #                ui.label('See, no shadow!')
#    #            with ui.card().classes('no-shadow border-[1px] w-64 h-32 justify-center items-center'):
#    #                ui.label('second card')
#        with ui.tab_panel(two):
#            ui.label('Second tab')
#


ui.run()
