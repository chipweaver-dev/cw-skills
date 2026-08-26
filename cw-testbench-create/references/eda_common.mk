#================================================================================
# eda tools version settings
#================================================================================
ifeq ($(VCS_VERSION), 2018)
	vcs = /share/eda/Synopsys/vcs/O-2018.09-SP2/bin/vcs
else ifeq ($(VCS_VERSION), 2020)
	vcs = /share/eda/Synopsys/vcs/Q-2020.03-SP2-7/bin/vcs
else
	vcs = /share/eda/Synopsys/vcs/Q-2020.03-SP2-7/bin/vcs
endif

ifeq ($(VERDI_VERSION), 2018)
	verdi = /share/eda/Synopsys/verdi/Verdi_O-2018.09-SP2/bin/verdi
else ifeq ($(VERDI_VERSION), 2020)
	verdi = /share/eda/Synopsys/verdi/R-2020.12-SP1/bin/verdi
else
	verdi = /share/eda/Synopsys/verdi/R-2020.12-SP1/bin/verdi
endif

LOG_DIR ?= ./out/$(shell whoami)

#================================================================================
# tb variable settings
#================================================================================
DEBUG_MODE ?= 0

# 根据模式选择时间戳格式
ifeq ($(DEBUG_MODE),1)
    # 调试模式：精度到天
    export TIMESTAMP ?= $(shell date +%Y%m%d)
    $(info DEBUG_MODE=1: Using day-level timestamp: $(TIMESTAMP))
else
    # 正常模式：精度到秒
    export TIMESTAMP ?= $(shell date +%Y%m%d_%H%M%S)
    $(info DEBUG_MODE=0: Using second-level timestamp: $(TIMESTAMP))
endif

#================================================================================
# targets
#================================================================================
#========================================
# vlogan
#========================================

vlogan_common_opt = -full64 -sverilog
vlogan_log_opt = -l $(LOG_DIR)/$(TIMESTAMP)_vlogan.log
vlogan:
	mkdir -p $(LOG_DIR) && \
	vlogan \
		$(vlogan_common_opt) \
		$(vlogan_log_opt) \
		$(vlogan_user_opt) \
		$(dut_ft_opt)



#========================================
# compile
#========================================

# comp_opt:
#   -debug_all 
#   -sverilog : Enables SystemVerilog construcs specified in the IEEE Standard of SystemVerilog, IEEE Std 1800-2009.
#   -ntb_opts uvm-1.1:  load UVM 1.1d 
#   -kdb: to generate Verdi Knowledge Database (KDB).
#   -V : Options for Controlling Messages, Verbose mode; compiles verbosely.
#   -timescale 1ns/1ps: Options to Specify the Tima scala, 
comp_common_opt = -full64 \
					 -sverilog \
					 -ntb_opts uvm-1.1 \
					 -kdb \
					 -debug_acc+all -debug_region+cell+encrypt \
					 -Vt \
					 -timescale=1ns/1ps

comp_log_opt = -l $(LOG_DIR)/$(TIMESTAMP)_comp.log

comp:
	mkdir -p $(LOG_DIR) && \
	$(vcs) \
		$(comp_common_opt) \
		$(snop_vip_opt) \
		$(comp_log_opt) \
		$(dut_ft_opt) \
		$(tb_ft_opt) \
		$(top_opt) \
		$(comp_user_opt)

#========================================
# run
#========================================
# run_common_opt:
#   +ntb_exit_on_error[=value] :  Causes VCS to exit when the value is less than
#   -V :Verbose mode
run_common_opt = +ntb_exit_on_error=20 \
								 -V 

run_tc_opt = +UVM_TESTNAME=$(tc)
run_log_opt = -l $(LOG_DIR)/$(tc)/$(TIMESTAMP)_run.log

run_tcl_opt ?= run.tcl
# run_ucli_opt:
#   -ucli : Unified Command Line Interface
#   -i : UCLI include file
run_ucli_opt = -ucli -i $(run_tcl_opt)

timeout ?= 10
run_timeout_opt = +timeout_ms=$(timeout)


run:
	mkdir -p $(LOG_DIR)/$(tc) && \
	mkdir -p $(WAVE_DIR)/$(tc) && \
	./simv \
		$(run_common_opt) \
		$(run_log_opt) \
		$(run_tc_opt) \
		$(run_timeout_opt) \
		$(run_user_opt) \
		$(run_ucli_opt)

#========================================
# comp && run
#========================================
all:
	$(MAKE) comp
	$(MAKE) run

#========================================
# verdi
#========================================

verdi_common_opt = -full64 -sv
verdi_log_opt = -logdir $(LOG_DIR)/verdi.log

verdi: 
	mkdir -p $(LOG_DIR) && \
	$(verdi) \
		$(verdi_common_opt) \
		$(verdi_log_opt) \
		$(snop_vip_opt) \
		$(dut_ft_opt) \
		$(tb_ft_opt) \
		$(top_opt) \
		$(comp_user_opt) \
		&

#========================================
# clean
#========================================
clean:
	rm -rf simv* xml_dump.log ucli* vc_hdrs.h csrc novas* 
clean_all:
	rm -rf log wave simv* xml_dump.log ucli* vc_hdrs.h csrc novas* 


.PHONY: print-%
# Print any variable and it's origin. This helps figure out where the
# variable was defined and to distinguish between empty and undefined.
print-%:
	@echo "$*=$($*)"
	@echo "Origin is: $(origin $*)"

