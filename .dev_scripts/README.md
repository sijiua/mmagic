# Scripts for developing MMEditing

- [1. Check UT](#check-ut)
- [2. Test all the models](#test-benchmark)
- [3. Train all the models](#3-train-all-the-models)
  - [3.1 Train for debugging](#31-train-for-debugging)
  - [3.2 Train for FP32](#32-train-for-fp32)
  - [3.3 Train for FP16](#33-train-for-fp16)
- [4. Monitor your training](#4-monitor-your-training)
- [5. Train with a list of models](#5-train-with-a-list-of-models)
- [6. Train with skipping a list of models](#6-train-with-skipping-a-list-of-models)

## 1. Check UT

Please check your UT by the following scripts:

```python
cd mmediting/
python .dev_script/update_ut.py
```

Then, you will find some redundant UT, missing UT and blank UT.
Please create UTs according to your package code implementation.

## 2. Test all the models

Please follow these steps to test all the models in MMEditing:

First, you will need download all the pre-trained checkpoints by:

```shell
python .dev_scripts/download_models.py
```

Then, you can start testing all the benchmarks by：

```shell
python .dev_scripts/test_benchmark.py
```

## 3. Train all the models

### 3.1 Train for debugging

In order to test all the pipelines of training, visualization, etc., you may want to set the total iterations of all the models as less steps (e.g., 100 steps) for quick evaluation. You can use the following steps:

First, since our datasets are stored in ceph, you need to create ceph configs.

```shell
# create configs
python .dev_scripts/create_ceph_configs.py \
        --target-dir configs_ceph_debug \
        --gpus-per-job 2 \
        --iters 100 \
        --save-dir-prefix work_dirs/benchmark_debug \
        --work-dir-prefix work_dirs/benchmark_debug
```

If you only want to update a specific config file, you can specify it by `--test-file configs/aot_gan/aot-gan_smpgan_4xb4_places-512x512.py`.

Here, `--target-dir` denotes the path of new created configs, `--gpus-per-job` denotes the numbers of gpus used for each job, `--iters` denotes the total iterations of each model, `--save-dir-prefix` and `--work-dir-prefix` denote the working directory, where you can find the working logging.

Then, you will need to submit all the jobs by running `train_benchmark.py`.

```shell
python .dev_scripts/train_benchmark.py mm_lol \
    --config-dir configs_ceph_debug \
    --run \
    --gpus-per-job 2 \
    --job-name debug \
    --work-dir work_dirs/benchmark_debug \
    --resume \
    --quotatype=auto
```

Here, you will specify the configs files used for training by `--config-dir`, submit all the jobs to run by set `--run`. You can set the prefix name of the submitted jobs by `--job-name`, specify the working directory by `--work-dir`. We suggest using `--resume` to enable auto resume during training and `--quotatype=auto` to fully exploit all the computing resources.

### 3.2 Train for FP32

If you want to train all the models with FP32 (i.e, regular settings as the same with `configs/`),
you can follow these steps:

```shell
# create configs for fp32
python .dev_scripts/create_ceph_configs.py \
        --target-dir configs_ceph_fp32 \
        --gpus-per-job 4 \
        --save-dir-prefix work_dirs/benchmark_fp32 \
        --work-dir-prefix work_dirs/benchmark_fp32 \
```

Then, submit the jobs to run by slurm:

```shell
python .dev_scripts/train_benchmark.py mm_lol \
    --config-dir configs_ceph_fp32 \
    --run \
    --resume \
    --gpus-per-job 4 \
    --job-name fp32 \
    --work-dir work_dirs/benchmark_fp32 \
    --quotatype=auto
```

### 3.3 Train for FP16

You will also need to train the models with AMP (i.e., FP16), you can use the following steps to achieve this:

```shell
python .dev_scripts/create_ceph_configs.py \
        --target-dir configs_ceph_amp \
        --gpus-per-job 4 \
        --save-dir-prefix work_dirs/benchmark_amp \
        --work-dir-prefix work_dirs/benchmark_amp
```

Then, submit the jobs to run:

```shell
python .dev_scripts/train_benchmark.py mm_lol \
    --config-dir configs_ceph_amp \
    --run \
    --resume \
    --gpus-per-job 4 \
    --amp \
    --job-name amp \
    --work-dir work_dirs/benchmark_amp \
    --quotatype=auto
```

# 4. Monitor your training

After you submitting jobs following [3-Train-all-the-models](#3-train-all-the-models), you will find a `xxx.log` file.
This log file list all the job name of job id you have submitted. With this log file, you can monitor your training by running `.dev_scripts/job_watcher.py`.

For example, you can run

```shell
python .dev_scripts/job_watcher.py --work-dir work_dirs/benchmark_fp32/ --log 20220923-140317.log
```

Then, you will find `20220923-140317.csv`, which reports the status and recent log of each job.

# 5. Train with a list of models

If you only need to run some of the models, you can list all the models' name in a file, and specify the models when using `train_benchmark.py`.

For example,

```shell
python .dev_scripts/train_benchmark.py mm_lol \
    --config-dir configs_ceph_fp32 \
    --run \
    --resume \
    --gpus-per-job 4 \
    --job-name fp32 \
    --work-dir work_dirs/benchmark_fp32 \
    --quotatype=auto \
    --rerun \
    --rerun-list 20220923-140317.log \
```

Specifically, you need to enable `--rerun`, and specify the list of models to rerun by `--rerun-list`

# 6. Train with skipping a list of models

If you want to train all the models while skipping some models, you can also list all the models' name in a file, and specify the models when running `train_benchmark.py`.

For example,

```shell
python .dev_scripts/train_benchmark.py mm_lol \
    --config-dir configs_ceph_fp32 \
    --run \
    --resume \
    --gpus-per-job 4 \
    --job-name fp32 \
    --work-dir work_dirs/benchmark_fp32 \
    --quotatype=auto \
    --skip \
    --skip-list 20220923-140317.log \
```

Specifically, you need to enable `--skip`, and specify the list of models to skip by `--skip-list`