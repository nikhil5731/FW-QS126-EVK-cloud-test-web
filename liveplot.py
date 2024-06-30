from dataclasses import dataclass
from typing import Literal
import matplotlib.pyplot as plt
import matplotlib.ticker as plt_ticker
import json
import dictobj
import os
import glob

@dataclass
class PlotSettings:
    y_label: str
    y_scale: Literal['linear', 'log']
    y_min: float
    y_max: float
    format: str
    data_keys: list[str]

    def matplotlib_ax_setup(self, ax: plt.Axes):
        self.ax = ax
        self.ax.xaxis.set_major_locator(plt_ticker.MaxNLocator(integer=True))

        self.ax.set_ylabel(self.y_label)
        self.ax.set_yscale(self.y_scale)
        if self.format == '%':
            self.ax.yaxis.set_major_formatter(plt_ticker.PercentFormatter(xmax=1.0))

        if self.y_min is not None and self.y_max is not None:
            self.ax.set_ylim(ymin=self.y_min, ymax=self.y_max)
        for key in self.data_keys:
            self.ax.plot([])
    
    def matplotlib_ax_update(self, values: list[list], averaging: int):
        for label, line, value in zip(self.data_keys, self.ax.lines, values):
            line.set_data(list(range(len(value))), value)
            # see link for other ways of drawing text: https://stackoverflow.com/questions/6319155/show-the-final-y-axis-value-of-each-line-with-matplotlib
            text = f'{label}: '
            count = 0
            accum = 0.0
            for v in value[-averaging:]:
                if v is None:
                    continue
                count += 1
                accum += v
            if value:
                match self.format:
                    case '%':
                        fmt = '.02%'
                    case _:
                        fmt = {
                            'linear': '.03f',
                            'log': '.03e'
                        }[self.y_scale]
                text += f'{accum/count:{fmt}}' if count else ''
            else:
                text += '(ERR)'
            line.set_label(text)
        self.ax.relim()
        self.ax.set_xlim(xmin=0, xmax=len(value)-1)
        self.ax.autoscale_view()
        self.ax.legend(loc='center left', bbox_to_anchor=(1, 0.5), fontsize=20)
        

class Plots:
    def __init__(self, plot_settings: list[PlotSettings]) -> None:
        self.plot_settings = plot_settings
        self.fig, self.axes = self.__create()

    def __create(self):
        fig, axes = plt.subplots(len(self.plot_settings), 1)
        if len(self.plot_settings) == 1:
            axes = [axes]
        for setting, ax in zip(self.plot_settings, axes):
            setting.matplotlib_ax_setup(ax)
        return fig, axes

    def update(self, data: list[dict], averaging: int = 1, window_title = ''):
        if window_title:
            self.fig.canvas.manager.set_window_title(window_title)
        all_values = get_values_all(self.plot_settings, data)
        for setting, values in zip(self.plot_settings, all_values):
            setting.matplotlib_ax_update(values, averaging)

@dataclass
class ConfigPlot:
    averaging: int
    plots: list[PlotSettings]

    @staticmethod
    def from_file(file_path: str):
        with open(file_path, 'r') as file:
            file_json = json.load(file)
        return dictobj.obj_from_dict(ConfigPlot, file_json)
    
    def to_file(self, file_path: str):
        as_dict = dictobj.dict_from_obj(self)
        with open(file_path, 'w') as file:
            json.dump(as_dict, file, indent='\t')
def get_json(file_path: str) -> ConfigPlot:
    if not os.path.exists(file_path):
        EXAMPLE_FILE = '''{
  "averaging": 3,
  "plots": [
    {
      "y_label": "BER",
      "y_scale": "log",
      "y_min": 1e-6,
      "y_max": 1e-1,
      "format": null,
      "data_keys": [
        "BER"
      ]
    },
    {
      "y_label": "PER",
      "y_scale": "linear",
      "y_min": 0.0,
      "y_max": 1.0,
      "format": "%",
      "data_keys": [
        "PER",
        "PMDR"
      ]
    },
    {
      "y_label": "dBm",
      "y_scale": "linear",
      "y_min": null,
      "y_max": null,
      "format": null,
      "data_keys": [
        "LinkMargin"
      ]
    },
    {
      "y_label": "s",
      "y_scale": "linear",
      "y_min": null,
      "y_max": null,
      "format": null,
      "data_keys": [
        "Latency"
      ]
    },
    {
      "y_label": "bps",
      "y_scale": "linear",
      "y_min": null,
      "y_max": null,
      "format": null,
      "data_keys": [
        "Throughput"
      ]
    }
  ]
}'''
        with open(file_path, 'w') as json_file:
            json_file.write(EXAMPLE_FILE)
        exit('missing json value, generating a default example, please configure and run again')
    return ConfigPlot.from_file(file_path)


def get_values(key, data: list[dict]) -> None | list[float]:
    if key not in data[0].keys():
        return []
    values = [float(row[key]) if row[key] else None for row in data]
    return values

def get_values_all(settings: list[PlotSettings], data: list[dict]):
    all_values = []
    for setting in settings:
        plot_values = []
        for key in setting.data_keys:
            plot_values.append(get_values(key, data))
        all_values.append(plot_values)
    return all_values

# see: https://stackoverflow.com/questions/39327032/how-to-get-the-latest-file-in-a-folder
def newest_csv(folder_path):
    csv_files = glob.glob(os.path.join(folder_path, '*.csv'))
    if not csv_files:
        exit('could not find file in specified directory')
    return max(csv_files, key=os.path.getctime)

def read_csv_and_update(plots: Plots, file_path: str):
    with open(file_path, 'r', newline='') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        csv_data = list(csv_reader)
    if not len(csv_data):
        return
    plots.update(data=csv_data, averaging=settings.averaging, window_title=os.path.splitext(os.path.basename(file_path))[0])


if __name__ == '__main__':
    import csv
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('file_path', help='path of the result file to graph, use a directory path for most recent live plotting')

    args = parser.parse_args()
    arg_file_path: str = args.file_path

    settings = get_json('local/config_plot.json')

    myplots = Plots(plot_settings=settings.plots)
    def auto_tight_layout(event):
        myplots.fig.tight_layout()
    myplots.fig.canvas.mpl_connect('resize_event', auto_tight_layout)


    if os.path.isdir(arg_file_path):
        plt.ion()
        while plt.fignum_exists(myplots.fig.number):
            newest_file = newest_csv(arg_file_path)
            read_csv_and_update(myplots, newest_file)
            plt.pause(0.2)
    else:
        read_csv_and_update(myplots, arg_file_path)

        plt.show()