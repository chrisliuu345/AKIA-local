"""数据工具集 — 随机生成器 / 格式转换 / 异常值检测"""

import pandas as pd, numpy as np
from PySide6.QtWidgets import (
    QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QFormLayout,QComboBox,QSpinBox,QDoubleSpinBox,QTableWidget,
    QTableWidgetItem,QStackedWidget,QMessageBox,
    QFileDialog,
)
from ui.tabs.base_tab import BaseAnalysisTab
from ui.theme import BUTTON_PRIMARY_STRETCH,BUTTON_SECONDARY,BUTTON_TOGGLE,FONT_18B
from ui.theme import colors as theme_colors
from core.data_generator import DataGenerator

class DataToolsTab(BaseAnalysisTab):
    def __init__(self,p=None): super().__init__(p); self._setup_ui()
    def _setup_ui(self):
        tc=theme_colors(); layout=QVBoxLayout(self); layout.setContentsMargins(12,12,12,12)
        self.title_label=QLabel("数据工具"); self.title_label.setFont(FONT_18B); layout.addWidget(self.title_label)
        mb=QHBoxLayout()
        self.btn_gen=QPushButton("随机生成"); self.btn_gen.setCheckable(True); self.btn_gen.setChecked(True); self.btn_gen.setStyleSheet(BUTTON_TOGGLE); self.btn_gen.clicked.connect(lambda:self._switch(0))
        self.btn_conv=QPushButton("格式转换"); self.btn_conv.setCheckable(True); self.btn_conv.setStyleSheet(BUTTON_TOGGLE); self.btn_conv.clicked.connect(lambda:self._switch(1))
        self.btn_out=QPushButton("异常值检测"); self.btn_out.setCheckable(True); self.btn_out.setStyleSheet(BUTTON_TOGGLE); self.btn_out.clicked.connect(lambda:self._switch(2))
        mb.addWidget(self.btn_gen); mb.addWidget(self.btn_conv); mb.addWidget(self.btn_out); mb.addStretch()
        layout.addLayout(mb)
        self.stack=QStackedWidget()
        self.stack.addWidget(self._gen_panel(tc))
        self.stack.addWidget(self._conv_panel(tc))
        self.stack.addWidget(self._outlier_panel(tc))
        layout.addWidget(self.stack)
        self.result=QTableWidget(); self.result.setAlternatingRowColors(True); layout.addWidget(self.result,1)
    def _switch(self,i):
        for b,j in [(self.btn_gen,0),(self.btn_conv,1),(self.btn_out,2)]: b.setChecked(j==i)
        self.stack.setCurrentIndex(i)

    def _on_dist_changed(self,dist):
        labels={
            "正态":("μ:","σ:"),
            "对数正态":("μ:","σ:"),
            "指数":("scale:",""),
            "均匀":("low:","high:"),
            "Weibull":("scale:","shape:"),
            "二项":("trials:","prob:"),
            "泊松":("λ:",""),
        }
        l1,l2=labels.get(dist,("μ/scale:","σ/shape:"))
        self.gen_mu_label.setText(l1)
        self.gen_sigma_label.setText(l2)
        self.gen_sigma.setVisible(l2!="")
        self.gen_mu.setVisible(l1!="")

    def _gen_panel(self,tc):
        w=QWidget(); l=QFormLayout(w)
        self.gen_dist=QComboBox(); self.gen_dist.addItems(DataGenerator.DISTS); self.gen_dist.currentTextChanged.connect(self._on_dist_changed); l.addRow("分布:",self.gen_dist)
        self.gen_n=QSpinBox(); self.gen_n.setRange(10,999999); self.gen_n.setValue(100); l.addRow("样本量:",self.gen_n)
        self.gen_mu=QDoubleSpinBox(); self.gen_mu.setRange(-9999,9999); self.gen_mu.setValue(10); self.gen_mu_label=QLabel("μ/scale:"); l.addRow(self.gen_mu_label,self.gen_mu)
        self.gen_sigma=QDoubleSpinBox(); self.gen_sigma.setRange(0.01,9999); self.gen_sigma.setValue(1); self.gen_sigma_label=QLabel("σ/shape:"); l.addRow(self.gen_sigma_label,self.gen_sigma)
        tmpl=QHBoxLayout()
        self.btn_spc_tmpl=QPushButton("SPC模板"); self.btn_spc_tmpl.setStyleSheet(BUTTON_SECONDARY); self.btn_spc_tmpl.clicked.connect(lambda:self._gen_template("spc"))
        self.btn_msa_tmpl=QPushButton("MSA模板"); self.btn_msa_tmpl.setStyleSheet(BUTTON_SECONDARY); self.btn_msa_tmpl.clicked.connect(lambda:self._gen_template("msa"))
        self.btn_doe_tmpl=QPushButton("DOE模板"); self.btn_doe_tmpl.setStyleSheet(BUTTON_SECONDARY); self.btn_doe_tmpl.clicked.connect(lambda:self._gen_template("doe"))
        tmpl.addWidget(self.btn_spc_tmpl); tmpl.addWidget(self.btn_msa_tmpl); tmpl.addWidget(self.btn_doe_tmpl)
        l.addRow("模板:",tmpl)
        self.btn_gen_run=QPushButton("生成数据"); self.btn_gen_run.setStyleSheet(BUTTON_PRIMARY_STRETCH); self.btn_gen_run.clicked.connect(self._do_gen)
        l.addRow(self.btn_gen_run)
        self.btn_gen_export=QPushButton("导出Excel"); self.btn_gen_export.setStyleSheet(BUTTON_SECONDARY); self.btn_gen_export.clicked.connect(self._export_gen)
        l.addRow(self.btn_gen_export)
        return w
    def _do_gen(self):
        dist=self.gen_dist.currentText(); n=self.gen_n.value()
        mu_val=self.gen_mu.value(); sigma_val=self.gen_sigma.value()
        if dist=="正态":
            data=DataGenerator.generate(dist,n,mu=mu_val,sigma=sigma_val)
        elif dist=="对数正态":
            data=DataGenerator.generate(dist,n,mu=mu_val,sigma=sigma_val)
        elif dist=="指数":
            data=DataGenerator.generate(dist,n,scale=mu_val)
        elif dist=="均匀":
            if mu_val >= sigma_val:
                QMessageBox.warning(self,"参数错误",f"W51: 均匀分布要求 low < high (当前 low={mu_val}, high={sigma_val})")
                return
            data=DataGenerator.generate(dist,n,low=mu_val,high=sigma_val)
        elif dist=="Weibull":
            data=DataGenerator.generate(dist,n,scale=mu_val,shape=sigma_val)
        elif dist=="二项":
            data=DataGenerator.generate(dist,n,trials=int(mu_val),prob=sigma_val)
        elif dist=="泊松":
            data=DataGenerator.generate(dist,n,lam=int(mu_val))
        else:
            data=DataGenerator.generate(dist,n)
        self._gen_df=pd.DataFrame({"value":data})
        self._show_df(self._gen_df)
    def _gen_template(self,t):
        if t=="spc": self._gen_df=DataGenerator.spc_template()
        elif t=="msa": self._gen_df=DataGenerator.msa_template()
        else: self._gen_df=DataGenerator.doe_template()
        self._show_df(self._gen_df)
    def _export_gen(self):
        if not hasattr(self,'_gen_df') or self._gen_df is None: return
        p,_=QFileDialog.getSaveFileName(self,"导出","generated.xlsx","Excel (*.xlsx)")
        if p: self._gen_df.to_excel(p,index=False); QMessageBox.information(self,"完成",f"已保存 {p}")

    def _conv_panel(self,tc):
        w=QWidget(); l=QFormLayout(w)
        self.conv_info=QLabel("拖入文件或点击选择, 自动检测格式并转换"); l.addRow(self.conv_info)
        btns=QHBoxLayout()
        self.btn_csv2xlsx=QPushButton("CSV→Excel"); self.btn_csv2xlsx.setStyleSheet(BUTTON_SECONDARY); self.btn_csv2xlsx.clicked.connect(lambda:self._convert("csv2xlsx"))
        self.btn_xlsx2csv=QPushButton("Excel→CSV"); self.btn_xlsx2csv.setStyleSheet(BUTTON_SECONDARY); self.btn_xlsx2csv.clicked.connect(lambda:self._convert("xlsx2csv"))
        self.btn_wide2long=QPushButton("宽→长"); self.btn_wide2long.setStyleSheet(BUTTON_SECONDARY); self.btn_wide2long.clicked.connect(lambda:self._convert("wide2long"))
        btns.addWidget(self.btn_csv2xlsx); btns.addWidget(self.btn_xlsx2csv); btns.addWidget(self.btn_wide2long)
        l.addRow("转换:",btns); return w
    def _convert(self,mode):
        if mode=="csv2xlsx":
            f,_=QFileDialog.getOpenFileName(self,"选择CSV","","CSV (*.csv)")
            if not f: return
            df=pd.read_csv(f); out=f.replace(".csv",".xlsx"); df.to_excel(out,index=False)
            QMessageBox.information(self,"完成",f"已保存 {out}")
        elif mode=="xlsx2csv":
            f,_=QFileDialog.getOpenFileName(self,"选择Excel","","Excel (*.xlsx)")
            if not f: return
            df=pd.read_excel(f); out=f.replace(".xlsx",".csv"); df.to_csv(out,index=False)
            QMessageBox.information(self,"完成",f"已保存 {out}")
        elif mode=="wide2long":
            if self.df is None: QMessageBox.information(self,"提示","请先导入数据"); return
            cols=list(self.df.columns); id_cols=[cols[0]]; val_cols=cols[1:]
            try:
                df_melt=pd.melt(self.df,id_vars=id_cols,value_vars=val_cols,var_name="variable",value_name="value")
                self._show_df(df_melt)
            except Exception as e: QMessageBox.critical(self,"错误",str(e))

    def _outlier_panel(self,tc):
        w=QWidget(); l=QFormLayout(w)
        self.out_method=QComboBox(); self.out_method.addItems(["IQR","Z-score","Grubbs"])
        l.addRow("方法:",self.out_method)
        self.out_col=QComboBox(); l.addRow("检测列:",self.out_col)
        self.btn_out_run=QPushButton("检测异常值"); self.btn_out_run.setStyleSheet(BUTTON_PRIMARY_STRETCH); self.btn_out_run.clicked.connect(self._do_outlier)
        l.addRow(self.btn_out_run); return w
    def set_data(self,df,info=None):
        BaseAnalysisTab.set_data(self,df,info)
        if df is not None:
            self.out_col.clear()
            for c in df.select_dtypes(include="number").columns: self.out_col.addItem(str(c))
    def _do_outlier(self):
        if self.df is None: return
        col=self.out_col.currentText(); method=self.out_method.currentText()
        if not col: return
        s=pd.to_numeric(self.df[col],errors="coerce").dropna()
        if method=="IQR":
            q1,q3=s.quantile(0.25),s.quantile(0.75); iqr=q3-q1
            lo,hi=q1-1.5*iqr,q3+1.5*iqr
            outliers=((s<lo)|(s>hi))
        elif method=="Z-score":
            z=np.abs((s-s.mean())/s.std())
            outliers=z>3
        else:
            from scipy import stats as sp_stats
            n=len(s)
            if n<3:
                outliers=pd.Series(False,index=s.index)
            else:
                mean_val=s.mean(); std_val=s.std()
                if std_val==0:
                    outliers=pd.Series(False,index=s.index)
                else:
                    t=sp_stats.t.ppf(1-0.05/(2*n),n-2)
                    g_crit=((n-1)/np.sqrt(n))*np.sqrt(t**2/(n-2+t**2))
                    g_max=(s.max()-mean_val)/std_val
                    g_min=(mean_val-s.min())/std_val
                    outliers=pd.Series(False,index=s.index)
                    if g_max>g_crit:
                        outliers[s.idxmax()]=True
                    if g_min>g_crit:
                        outliers[s.idxmin()]=True
        flagged=s[outliers]
        hdrs=["行号","值","判定"]; self.result.setColumnCount(3); self.result.setHorizontalHeaderLabels(hdrs)
        self.result.setRowCount(len(flagged))
        for i,(idx,v) in enumerate(flagged.items()):
            self.result.setItem(i,0,QTableWidgetItem(str(idx)))
            self.result.setItem(i,1,QTableWidgetItem(f"{v:.4f}"))
            self.result.setItem(i,2,QTableWidgetItem("异常"))
        self.result.resizeColumnsToContents()

    def _show_df(self,df):
        self.result.setColumnCount(len(df.columns)); self.result.setHorizontalHeaderLabels(list(df.columns))
        m=min(100,len(df)); self.result.setRowCount(m)
        for i in range(m):
            for j,c in enumerate(df.columns): self.result.setItem(i,j,QTableWidgetItem(str(df.iloc[i,j])))
        self.result.resizeColumnsToContents()
